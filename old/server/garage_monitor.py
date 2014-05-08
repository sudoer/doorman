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
# HARDWARE
PIN_DOOR = 'd1'
PIN_STATUSLED = 'd2'
PIN_LIGHTMETER = 'a1'
RFCOMM_DEV = 0
RFCOMM_CH = 0
RFCOMM_BAUD = 19200
BT2S_MAC = 'aa:aa:aa:aa:aa:aa'
BT2S_PIN = '0000'
# TIMING
PERIOD_DOOR = 10
PERIOD_LIGHT = 10
PERIOD_LOG = 360
PROWL_TRIGGER = 3
COUNT_LED_OPEN = 3
COUNT_LED_CLOSED = 10
LOOP_TIME = 0.25
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

def log_info(string):
   timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   g_logFD.write(timeStamp+" "+string+"\n")
   g_logFD.flush()
   os.fsync(g_logFD)

#-----------------------------------------------------------

def log_debug(string):
   #timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
   #g_logFD.write(timeStamp+" "+string+"\n")
   #g_logFD.flush()
   #os.fsync(g_logFD)
   pass

#-----------------------------------------------------------
#  MONITORING
#-----------------------------------------------------------

def monitor():
   timeNow = time.time()
   log_info("monitoring, timeNow=["+("%.2f"%timeNow)+"]")
   ser = serial.Serial('/dev/rfcomm'+('%d'%RFCOMM_DEV), RFCOMM_BAUD, timeout=0.1)
   # initial value of timers
   checkLightTime = time.time()
   checkDoorTime = time.time()
   checkLedTime = time.time()
   logTime = time.time()
   # initial status values
   ledState = 0
   ledBlinker = 0
   brightness = 0
   doorIsOpen = 0
   doorWasOpen = 0
   doorCount = 0
   doorDateTime = None

   # Turn ECHO off.
   ser.write("e-\n")

   # loop forever
   while 1:
      # master clock, used to see when to poll things
      timeNow = time.time()
      # defaults
      refreshStatusFile = False
      # Read everything you can from the serial port
      responses = ser.readlines()
      for line in responses:
         line = line.rstrip()
         # Proper responses begin with a "*".
         if line[0:1] == '*':
            log_debug("line=["+line+"]")
            # Look for "a6=257" (where a6 is the PIN_LIGHTMETER).
            if line[1:1+len(PIN_LIGHTMETER)+1] == PIN_LIGHTMETER+"=":
               darkness = int(line[1+len(PIN_LIGHTMETER)+1:])
               brightness = (1024-darkness)*100/1024
               refreshStatusFile = True
               log_debug("brightness=["+("%d"%brightness)+"%]")
            # Look for "d3=1" (where d3 is the PIN_DOOR).
            elif line[1:1+len(PIN_DOOR)+1] == PIN_DOOR+"=":
               # 5v mean door closed, 0v means door open.
               doorIsOpen = 1 - int(line[1+len(PIN_DOOR)+1:])
               if doorIsOpen != doorWasOpen:
                  log_info("door state changed")
                  doorCount = 0
                  doorDateTime = datetime.datetime.now()
               doorCount += 1
               # Debounce the door input, ignore a one-time blip.
               if doorCount == PROWL_TRIGGER:
                  # Only send a prowl notification after the door has
                  # CHANGED state, not on the first reading.
                  if doorDateTime is not None:
                     doorState = ("open" if doorIsOpen else "closed")
                     doorVerb = ("opened" if doorIsOpen else "closed")
                     doorTimestamp = doorDateTime.strftime('%m/%d %H:%M')
                     log_info(("%d"%PROWL_TRIGGER)+" consistent 'door "+doorState+"' events received")
                     log_info("sending a prowl notification")
                     script = os.environ['HOME']+"/bin/prowl.sh"
                     rc = shell([script, 'garage door '+doorState,
                        'garage door was '+doorVerb+' at '+doorTimestamp])
               doorWasOpen = doorIsOpen
               refreshStatusFile = True
         else:
            log_debug("junk=["+line+"]")

      # Write to status file if there have been changes.
      if refreshStatusFile:
         timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
         brightString = ("%d"%brightness)+"%"
         doorState = ("OPEN" if doorIsOpen else "CLOSED")
         # Write the status to a temp file.
         tmpFile = g_statusFile+".tmp"
         fd = open(tmpFile,'w+')
         fd.write("TIME="+timeStamp+"\n")
         fd.write("BRIGHTNESS="+brightString+"\n")
         fd.write("DOOR="+doorState+"\n")
         fd.close()
         log_debug("writing status file (D="+("1" if doorIsOpen else "0")+",B="+("%d"%brightness)+")")
         # atomic replacement
         os.rename(tmpFile,g_statusFile)

      # Log the door state every so often.
      if timeNow-logTime > PERIOD_LOG:
         logTime = timeNow
         brightString = ("%d"%brightness)+"%"
         doorState = ("OPEN" if doorIsOpen else "CLOSED")
         log_info("light="+brightString+" door="+doorState)

      # Read the magnetic reed switch.
      if timeNow-checkDoorTime > PERIOD_DOOR:
         checkDoorTime = timeNow
         ser.write(PIN_DOOR+"?\n")

      # Read the light sensor.
      if timeNow-checkLightTime > PERIOD_LIGHT:
         checkLightTime = timeNow
         ser.write(PIN_LIGHTMETER+"?\n")

      # Blink LED - fast if door is open, slow if door is closed.
      ledBlinker += 1
      if doorIsOpen and ( ledBlinker > COUNT_LED_OPEN ) : ledBlinker = 0
      if ( not doorIsOpen ) and ( ledBlinker > COUNT_LED_CLOSED ) : ledBlinker = 0
      if ledBlinker == 0:
         ser.write(PIN_STATUSLED+"="+("%d"%ledState)+"\n")
         ledState = 0 if ledState else 1

      time.sleep(LOOP_TIME)

#-----------------------------------------------------------
#  LAUNCHING
#-----------------------------------------------------------

def background(list):
   log_info("background command = "+(" ".join(list)))
   list.insert(0,sys.executable)
   p = subprocess.Popen(list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
   log_info("")
   return p

#-----------------------------------------------------------

def shell(list):
   global g_logFD
   log_info("shell command = "+(" ".join(list)))
   rc = subprocess.call(list, stdout=g_logFD, stderr=g_logFD)
   log_info("shell rc = "+("%d"%rc))
   log_info("")
   return rc

#-----------------------------------------------------------

#START

init()
while True:
   rc = shell(["sudo", "/usr/bin/l2ping", "-c1", BT2S_MAC])
   if rc != 0:
      log_info("mac "+BT2S_MAC+" not found")
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
            log_info("serial port exception, will retry")
         except:
            print "Unexpected error:", sys.exc_info()[0]
      rc = shell(["sudo", "/usr/bin/rfcomm", "release", '%d'%RFCOMM_DEV])
   time.sleep(10)
#END

#-----------------------------------------------------------

