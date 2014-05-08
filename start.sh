#!/bin/bash
date > start.log
cd /root/garage/doorman/raspi
./monitor.py >> start.log 2>&1 &

