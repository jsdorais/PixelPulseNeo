#!/bin/bash
echo "Time, RSS (KB), %MEM"
while true; do
    data=$(ps aux | grep "Matrix.driver.executor" | grep -v grep | awk '{print $6","$4}')
    echo "$(date '+%H:%M'), $data"
    sleep 300  # every 5 minutes
done
