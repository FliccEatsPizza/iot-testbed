#!/bin/bash

# gateway_startup.sh - Automatic Gateway Registration Script
# This script runs on Raspberry Pi startup to automatically register the gateway

# Configuration
SCRIPT_DIR="/home/pi/gateway_client"
PYTHON_SCRIPT="$SCRIPT_DIR/auto_register.py"
LOG_FILE="/home/pi/gateway_startup.log"
LOCK_FILE="/tmp/gateway_startup.lock"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to cleanup on exit
cleanup() {
    rm -f "$LOCK_FILE"
    log_message "Gateway startup script cleanup completed"
}

# Set trap for cleanup
trap cleanup EXIT

# Check if script is already running
if [ -f "$LOCK_FILE" ]; then
    log_message "Gateway startup script is already running. Exiting."
    exit 1
fi

# Create lock file
touch "$LOCK_FILE"

log_message "=== Gateway Startup Script Started ==="

# Wait for system to fully boot (optional delay)
log_message "Waiting for system to fully initialize..."
sleep 30

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    log_message "ERROR: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Make sure Python script is executable
chmod +x "$PYTHON_SCRIPT"

# Check if we have network connectivity (ping Google DNS)
log_message "Checking network connectivity..."
max_network_attempts=30
network_attempt=0

while [ $network_attempt -lt $max_network_attempts ]; do
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        log_message "Network connectivity confirmed"
        break
    fi
    
    network_attempt=$((network_attempt + 1))
    log_message "Waiting for network... (attempt $network_attempt/$max_network_attempts)"
    sleep 5
done

if [ $network_attempt -eq $max_network_attempts ]; then
    log_message "ERROR: Network connectivity timeout. Cannot proceed with registration."
    exit 1
fi

# Run the Python auto-registration script
log_message "Starting automatic gateway registration..."
cd "$SCRIPT_DIR"

# Run with Python3 and capture exit code
python3 "$PYTHON_SCRIPT"
exit_code=$?

if [ $exit_code -eq 0 ]; then
    log_message "Gateway registration completed successfully!"
else
    log_message "Gateway registration failed with exit code: $exit_code"
    log_message "Check the Python script logs for more details."
fi

log_message "=== Gateway Startup Script Completed ==="
exit $exit_code
