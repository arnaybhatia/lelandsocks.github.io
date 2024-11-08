#!/bin/bash

# Function to check if the current time is within the desired range
is_market_open() {
    current_time=$(date -u +%H:%M)
    echo "Current UTC Time: $current_time"
    market_open="14:00"
    market_close="21:30"

    if [[ "$current_time" > "$market_open" && "$current_time" < "$market_close" ]]; then
        return 0
    else
        return 1
    fi
}

while true
do
    if is_market_open; then
        cd /home/supersketchy/git/lelandstocks.github.io
        pixi run all
    else
        echo "Market Closed! Sleeping for 15 minutes..."
    fi
    sleep 900
done
