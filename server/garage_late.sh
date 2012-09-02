#!/bin/bash

doorinfo="$HOME/var/lib/garage.info"

if [[ $( grep -c "DOOR=OPEN" $doorinfo ) -gt 0 ]] ; then
   # make sure the date in the status file is today's (monitor program's not crashed)
   if [[ $( grep -c "$(date +%F)" $doorinfo ) -gt 0 ]] ; then
      # send a message
      $HOME/bin/prowl.sh 'garage door open late' "It's $(date +%H:%M) and the garage door is still open." > /dev/null
      # wait for bender to say the time (every hour)
      sleep 20
      # speak a warning
      TXT="/tmp/$$.txt"
      WAV="/tmp/$$.wav"
      echo "the garage door is open" >> $TXT
      flite -f $TXT -o $WAV
      mplayer -nolirc -ao oss -vo null $WAV > /dev/null
      rm $TXT $WAV
   fi
fi

