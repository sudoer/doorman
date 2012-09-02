#!/usr/bin/python

import os
import serial
import time
import sys
import subprocess
import datetime

# You should have a short file named "garage_settings.py"
# that contains these lines, with your own values.  That
# way, YOUR settings will be retained even if you pull
# down a new version of this program file.
PIN_DOOR = 'd1'
PIN_STATUSLED = 'd2'
PIN_LIGHTMETER = 'a1'
RFCOMM_DEV = 0
RFCOMM_CH = 0
RFCOMM_BAUD = 19200
BT2S_MAC = 'aa:aa:aa:aa:aa:aa'
BT2S_PIN = '0000'
PERIOD_DOOR = 10
PERIOD_LIGHT = 10
PERIOD_LOG = 360
COUNT_LED_OPEN = 3
COUNT_LED_CLOSED = 10
PROWL_TRIGGER = 3
# END of garage_settings.py

# these override the defaults above
from garage_settings import *

# globals
g_logFD = None
g_statusFile = None

#-----------------------------------------------------------

def init():
   # we're writing these globals
   global g_logFD
   global g_statusFile
   # log file
   logdir = os.environ['HOME']+"/var/log"
   if not os.path.exists(logdir):
      os.makedirs(logdir)
   logfile = logdir+"/garage.log"
   g_logFD = open(logfile,'a')
   # status file
   statusDir = os.environ['HOME']+"/var/lib"
   if not os.path.exists(statusDir):
      os.makedirs(statusDir)
   g_statusFile = statusDir+"/garage.info"

#-----------------------------------------------------------

def log(string):
   timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   g_logFD.write(timeStamp+" "+string+"\n")
   g_logFD.flush()
   os.fsync(g_logFD)

#-----------------------------------------------------------
#  MONITORING
#-----------------------------------------------------------

def monitor():
   timeNow = time.time()
   log("monitoring timeNow=["+("%.2f"%timeNow)+"]")
   ser = serial.Serial('/dev/rfcomm'+('%d'%RFCOMM_DEV), RFCOMM_BAUD, timeout=0.1)
   checkLightTime = time.time()
   checkDoorTime = time.time()
   checkLedTime = time.time()
   logTime = time.time()
   # we might read these before setting them
   ledState = 0
   ledBlinker = 0
   brightness = 0
   doorIsOpen = 0
   doorWasOpen = 0
   doorCount = 0
   doorDateTime = None

   while 1:
      timeNow = time.time()
      #log("timeNow=["+("%.2f"%timeNow)+"]")

      responses = ser.readlines()

      refreshStatusFile = False
      for line in responses:
         line = line.rstrip()
         if line[0:1] == '*':
            #log("line=["+line+"]")
            if line[1:1+len(PIN_LIGHTMETER)+1] == PIN_LIGHTMETER+"=":
               darkness = int(line[1+len(PIN_LIGHTMETER)+1:])
               brightness = (1024-darkness)*100/1024
               refreshStatusFile = True
               #log("brightness=["+("%d"%brightness)+"%]")
            elif line[1:1+len(PIN_DOOR)+1] == PIN_DOOR+"=":
               # 5v mean door closed, 0v means door open
               doorIsOpen = 1 - int(line[1+len(PIN_DOOR)+1:])
               if doorIsOpen != doorWasOpen:
                  log("door state changed")
                  doorCount = 0
                  doorDateTime = datetime.datetime.now()
               doorCount += 1
               if doorCount == PROWL_TRIGGER and doorDateTime is not None:
                  doorState = ("open" if doorIsOpen else "closed")
                  doorVerb = ("opened" if doorIsOpen else "closed")
                  doorTimestamp = doorDateTime.strftime('%m/%d %H:%M')
                  log(("%d"%PROWL_TRIGGER)+" consistent 'door "+doorState+"' events received")
                  log("sending a prowl notification")
                  script = os.environ['HOME']+"/bin/prowl.sh"
                  rc = shell([script, 'garage door '+doorState,
                     'garage door was '+doorVerb+' at '+doorTimestamp])
               doorWasOpen = doorIsOpen
               refreshStatusFile = True
         #else:
         #   log("junk=["+line+"]")

      # write to status file if there are refreshStatusFile
      if refreshStatusFile:
         timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
         brightString = ("%d"%brightness)+"%"
         doorState = ("OPEN" if doorIsOpen else "CLOSED")
         fd = open(g_statusFile,'w+')
         fd.write("TIME="+timeStamp+"\n")
         fd.write("BRIGHTNESS="+brightString+"\n")
         fd.write("DOOR="+doorState+"\n")
         fd.close()

      # log the state every so often
      if timeNow-logTime > PERIOD_LOG:
         logTime = timeNow
         brightString = ("%d"%brightness)+"%"
         doorState = ("OPEN" if doorIsOpen else "CLOSED")
         log("light="+brightString+" door="+doorState)

      # read magnetic reed switch
      if timeNow-checkDoorTime > PERIOD_DOOR:
         checkDoorTime = timeNow
         ser.write(PIN_DOOR+"?\n")

      # read light meter
      if timeNow-checkLightTime > PERIOD_LIGHT:
         checkLightTime = timeNow
         ser.write(PIN_LIGHTMETER+"?\n")

      # blink led - fast if door open, slow if door closed
      ledBlinker += 1
      if doorIsOpen and ( ledBlinker > COUNT_LED_OPEN ) : ledBlinker = 0
      if ( not doorIsOpen ) and ( ledBlinker > COUNT_LED_CLOSED ) : ledBlinker = 0
      if ledBlinker == 0:
         ser.write(PIN_STATUSLED+"="+("%d"%ledState)+"\n")
         ledState = 0 if ledState else 1

      time.sleep(0.25)

#-----------------------------------------------------------
#  LAUNCHING
#-----------------------------------------------------------

def background(list):
   log("background command = "+(" ".join(list)))
   list.insert(0,sys.executable)
   p = subprocess.Popen(list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   return p

#-----------------------------------------------------------

def shell(list):
   global g_logFD
   log("shell command = "+(" ".join(list)))
   rc = subprocess.call(list, stdout=g_logFD, stderr=g_logFD)
   log("shell rc = "+("%d"%rc))
   return rc

#-----------------------------------------------------------

#START

init()
while True:
   rc = shell(["sudo", "/usr/bin/l2ping", "-c1", BT2S_MAC])
   if rc != 0:
      log("mac "+BT2S_MAC+" not found")
   else:
      rc = shell(["sudo", "/usr/bin/rfcomm", "release", '%d'%RFCOMM_DEV])
      time.sleep(1)
      rc = shell(['sudo', '/usr/bin/rfcomm', 'bind', '%d'%RFCOMM_DEV, BT2S_MAC, '%d'%RFCOMM_CH])
      time.sleep(1)
      p = background(['sudo', '/usr/bin/rfcomm', 'connect', '%d'%RFCOMM_DEV, BT2S_MAC, '%d'%RFCOMM_CH])
      time.sleep(1)
      time.sleep(1)
      rc = shell(["ls", "-l", "/dev/rfcomm"+('%d'%RFCOMM_DEV)])
      rc = shell(["rfcomm"])
      time.sleep(1)
      # rc = shell(["sudo", "/usr/bin/bluetooth-agent", BT2S_PIN, BT2S_MAC])
      # time.sleep(1)
      rc = shell(["/usr/bin/rfcomm", "show", '%d'%RFCOMM_DEV])
      if rc == 0:
         try:
            monitor()
         except serial.serialutil.SerialException:
            log("serial port exception, will retry")
      rc = shell(["sudo", "/usr/bin/rfcomm", "release", '%d'%RFCOMM_DEV])
   time.sleep(10)
#END

#-----------------------------------------------------------

