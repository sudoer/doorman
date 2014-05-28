#!/usr/bin/python

import os
import time
import sys
import subprocess
import datetime
import ConfigParser

# Adafruit LCD plate I2C library
sys.path.append('/root/garage/Adafruit-Raspberry-Pi-Python-Code/Adafruit_CharLCDPlate')
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate

# Prowl notification library
sys.path.append('/root/garage/prowlpy')
import prowlpy

# GLOBALS
g_lcd = Adafruit_CharLCDPlate()
g_logFD = None
g_ledOverrideCounter = 0

class preferences:
    pass

# CONSTANTS
YESTERYEAR = datetime.datetime(1999, 12, 31)

# TIMING
PERIOD_STATUS = 5
PERIOD_LOG = 600
PERIOD_TEST = None
DEBOUNCE = 8
LOOP_TIME = 0.25
NOTIFICATION_VISUAL_DELAY = 2.5

# BUTTONS
BUTTON_MAP = {
    'SELECT': g_lcd.SELECT,
    'UP':     g_lcd.UP,
    'DOWN':   g_lcd.DOWN,
    'LEFT':   g_lcd.LEFT,
    'RIGHT':  g_lcd.RIGHT,
}

#-----------------------------------------------------------
#  PLUMBING
#-----------------------------------------------------------

def shell_capture(cmdargs) :
    global g_logFD
    log_debug('shell_capture command >> '+(' '.join(cmdargs)))
    p = subprocess.Popen(cmdargs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    log_debug("shell_capture done, rc="+('%d'%rc))
    return rc, stdout, stderr

#-----------------------------------------------------------

def log_info(string):
    global g_logFD
    timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    g_logFD.write(timeStamp+" "+string+"\n")
    g_logFD.flush()
    os.fsync(g_logFD)

#-----------------------------------------------------------

def log_debug(string):
    global g_logFD
    #timeStamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #g_logFD.write(timeStamp+" "+string+"\n")
    #g_logFD.flush()
    #os.fsync(g_logFD)
    pass

#-----------------------------------------------------------
#  NOTIFICATONS
#-----------------------------------------------------------

# TODO - separate this into another file
def notify(event,description):
    global preferences
    global g_ledOverrideCounter

    log_info('PROWL >> '+event+' | '+description)
    p = prowlpy.Prowl(preferences.prowl_api_key)
    try:
        p.post(application=preferences.prowl_app,
            event=event,
            description=description,
            priority=0,
            providerkey=None,
            url=None)
        log_info('prowl success')
    except Exception,msg:
        log_info('prowl error: '+msg)
    # override the normal LED blinking for this many loops
    g_ledOverrideCounter = 12

#-----------------------------------------------------------
#  MONITORING
#-----------------------------------------------------------

def monitor():

    global preferences
    global g_lcd
    global g_ledOverrideCounter

    doorCount = 0
    doorIsOpen = None
    doorWasOpen = None
    doorDateTime = None
    statusTime = YESTERYEAR
    logTime = YESTERYEAR
    testTime = datetime.datetime.now()
    ledBlinkCounter = 0

    g_lcd.begin(16, 2)
    g_lcd.clear()
    g_lcd.message("Adafruit RGB LCD\nPlate w/Keypad!")

    # loop forever
    while True:
        timeNow = datetime.datetime.now()

        somethingChanged = False

        # read door switch
        door = g_lcd.buttonPressed(preferences.DOOR_BUTTON)
        norm = preferences.DOOR_NORMALLY_OPEN
        test = g_lcd.buttonPressed(preferences.TEST_BUTTON)
        doorIsOpen = ( ( door == norm ) or test )

        # did door change?
        if doorIsOpen != doorWasOpen:
            somethingChanged = True
            if doorWasOpen is None:
                # Special case - startup
                doorWasOpen = doorIsOpen
                doorDateTime = timeNow
                log_info("door state initialized to '"+("open" if doorIsOpen else "closed")+"'")
            else:
                doorCount += 1
                log_info("door state changed, reading #%d" % doorCount)
                # update the status when the door opens/closes
        else:
            doorCount = 0

        # We can test notifications by forcing a state change.
        if PERIOD_TEST is not None:
            if timeNow-testTime > datetime.timedelta(seconds=PERIOD_TEST):
                log_info("changing the door state for testing purposes")
                doorIsOpen = not doorIsOpen
                doorCount = DEBOUNCE

        # Debounce the door input, ignore a one-time blip.
        if doorCount == DEBOUNCE:
            # Only send a prowl notification after the door has
            # CHANGED state, not on the first reading.
            if doorWasOpen is not None:
                doorState = ("open" if doorIsOpen else "closed")
                doorVerb = ("opened" if doorIsOpen else "closed")
                log_info(("%d"%DEBOUNCE)+" consistent 'door "+doorState+"' readings")
                event='garage door '+doorState
                description='garage door was '+doorVerb+' at '+timeNow.strftime('%m/%d %I:%M%p')
                notify(event, description)
            # Remember our new door state for later comparison.
            doorWasOpen = doorIsOpen
            doorDateTime = timeNow
            # update the status when we send a message
            somethingChanged = True

        # If some time has passed, or if the door has moved, then log it.
        if timeNow-statusTime > datetime.timedelta(seconds=PERIOD_STATUS) or somethingChanged:
            statusTime = timeNow
            # Write the status to a temp file.
            tmpFile = preferences.statusfile+".tmp"
            fd = open(tmpFile,'w+')
            fd.write("TIME="+timeNow.strftime('%Y-%m-%d %H:%M:%S')+"\n")
            fd.write("DOOR="+("OPEN" if doorIsOpen else "CLOSED")+"\n")
            fd.write("SINCE="+doorDateTime.strftime('%Y-%m-%d %H:%M:%S')+"\n")
            fd.close()
            log_debug("writing status file (D="+("1" if doorIsOpen else "0")+")")
            # atomic replacement
            os.rename(tmpFile,preferences.statusfile)

        # Log the door state every so often.
        if timeNow-logTime > datetime.timedelta(seconds=PERIOD_LOG):
            logTime = timeNow
            log_info("door="+("OPEN" if doorIsOpen else "CLOSED"))

        # Cron job will drop a file here, telling us to warn if door is still open.
        if os.path.exists(preferences.triggerfile):
            if doorIsOpen:
                log_info("it's late -- door is open")
                event = 'garage door open late'
                description = "It's "+timeNow.strftime('%I:%M%p') +" and the garage door is still open."
                notify(event, description)
            else:
                log_info("it's late -- door is closed -- good")
            os.remove(preferences.triggerfile)

        # LED BACKLIGHT

        if somethingChanged:
            ledBlinkCounter = 0
        ledBlinkCounter += 1

        # RED, YELLOW, GREEN, TEAL, BLUE, VIOLET, ON, OFF

        # Sending a message this takes priority over normal blinking.
        if g_ledOverrideCounter > 0:
            g_lcd.backlight(g_lcd.YELLOW)
            g_ledOverrideCounter -= 1
            # When we finish the override,
            # start back at the beginning of the color cycle.
            ledBlinkCounter = 0

        elif doorIsOpen:
            if ledBlinkCounter < 10:
                g_lcd.backlight(g_lcd.RED)
            else:
                g_lcd.backlight(g_lcd.VIOLET)
                ledBlinkCounter = 0

        elif ( not doorIsOpen ):
            if ledBlinkCounter < 12:
                g_lcd.backlight(g_lcd.GREEN)
            else:
                g_lcd.backlight(g_lcd.TEAL)
                ledBlinkCounter = 0

        time.sleep(LOOP_TIME)

        # LCD DISPLAY

        g_lcd.clear()
        # 12:34:56_CLOSED_
        # 192.168.101.202_
        g_lcd.message(timeNow.strftime('%H:%M:%S')+' '+("OPEN" if doorIsOpen else "CLOSED")+"\n"+ipAddr)


#-----------------------------------------------------------
#  MAIN
#-----------------------------------------------------------

#START

# TODO - can I just read this as a big tree and traverse it later?
config = ConfigParser.RawConfigParser()
config.read('settings.cfg')
preferences.DOOR_BUTTON = BUTTON_MAP[config.get('hardware', 'DOOR_BUTTON')]
preferences.TEST_BUTTON = BUTTON_MAP[config.get('hardware', 'TEST_BUTTON')]
preferences.DOOR_NORMALLY_OPEN = config.get('hardware', 'DOOR_NORMALLY_OPEN')
preferences.prowl_api_key = config.get('prowl', 'API_KEY')
preferences.prowl_app = config.get('prowl', 'APPLICATION')

# log file
preferences.logfile = config.get('paths', 'LOG_FILE')
tmpdir = os.path.dirname(preferences.logfile)
if not os.path.exists(tmpdir):
    os.makedirs(tmpdir)
g_logFD = open(preferences.logfile,'a')

# status file
preferences.statusfile = config.get('paths', 'STATUS_FILE')
tmpdir = os.path.dirname(preferences.statusfile)
if not os.path.exists(tmpdir):
    os.makedirs(tmpdir)

# trigger file
preferences.triggerfile = config.get('paths', 'TRIGGER_FILE')
tmpdir = os.path.dirname(preferences.triggerfile)
if not os.path.exists(tmpdir):
    os.makedirs(tmpdir)

cmd = [ '/bin/bash', '-c', 'ip addr show dev wlan0 | grep -o "inet [0-9.]*" | sed -e "s/inet //g"' ]
(rc,stdout,stderr) = shell_capture(cmd)
ipAddr = stdout.rstrip('\n')
log_info("IP address = '"+ipAddr+"'")

while True:
    try:
        monitor()
    except KeyboardInterrupt:
        g_lcd.clear()
        g_lcd.message('OUT OF SERVICE')
        g_lcd.backlight(g_lcd.OFF)
        print ""
        print "GAME OVER"
        break
    except:
        print "Unexpected error:", sys.exc_info()[0]
    time.sleep(10)

#END

#-----------------------------------------------------------

