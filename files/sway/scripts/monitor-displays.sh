#!/usr/bin/env bash

# monitor-displays.sh
# 
# This script monitors for display configuration changes using Sway's IPC protocol
# and runs set_displays.py to apply appropriate display settings when changes occur.
#
# It will continue running in the background, watching for any display connections,
# disconnections, or configuration changes.

# Exit on error, undefined variables, and pipe failures
set -euo pipefail

# Path to the display configuration script
DISPLAY_SCRIPT="$HOME/.config/sway/scripts/set_displays.py"

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $@"
}

# Check if set_displays.py exists and is executable
if [ ! -x "$DISPLAY_SCRIPT" ]; then
    log "ERROR: $DISPLAY_SCRIPT not found or not executable"
    exit 1
fi

# Check if running under Sway
if [ -z "${SWAYSOCK:-}" ]; then
    log "ERROR: SWAYSOCK environment variable not set. Are you running Sway?"
    exit 1
fi

log "Starting display monitor service..."
log "Monitoring for display changes using Sway IPC..."

# A small debounce mechanism to prevent multiple rapid executions
# when many output events happen in sequence (common during display changes)
execute_with_debounce() {
    # If there's already a pending execution within 2 seconds, do nothing
    if [ -n "${LAST_RUN:-}" ] && [ $(($(date +%s) - LAST_RUN)) -lt 2 ]; then
        log "Debouncing rapid display changes..."
        return
    fi
    
    log "Display change detected - executing $DISPLAY_SCRIPT"
    LAST_RUN=$(date +%s)
    
    # Execute the display script and capture any errors
    if ! $DISPLAY_SCRIPT; then
        log "ERROR: Failed to execute $DISPLAY_SCRIPT"
    else
        log "Display configuration updated successfully"
    fi
}

# Handle script termination gracefully
trap 'log "Display monitor service stopping..."; exit 0' INT TERM

# Main monitoring loop
# Subscribe to output events from Sway and process them
log "Waiting for display events..."
swaymsg -t subscribe '["output"]' --monitor | while read -r line; do
    # Check if the output event indicates a meaningful change
    if echo "$line" | grep -q "change"; then
        execute_with_debounce
    fi
done &

# If the swaymsg subscription fails, handle the error
if ! wait $!; then
    log "ERROR: Sway IPC subscription failed. Is Sway running correctly?"
    exit 1
fi

