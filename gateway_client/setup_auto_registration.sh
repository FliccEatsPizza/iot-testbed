#!/bin/bash

# setup_auto_registration.sh - Setup script for automatic gateway registration on Raspberry Pi

set -e

# Configuration
GATEWAY_CLIENT_DIR="/home/pi/gateway_client"
SERVICE_FILE="gateway-auto-register.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=== Gateway Auto-Registration Setup ==="

# Check if running as root for systemd operations
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run as root for systemd service installation."
    echo "Please run: sudo $0"
    exit 1
fi

# Create gateway_client directory if it doesn't exist
if [ ! -d "$GATEWAY_CLIENT_DIR" ]; then
    echo "Creating gateway_client directory..."
    mkdir -p "$GATEWAY_CLIENT_DIR"
    chown pi:pi "$GATEWAY_CLIENT_DIR"
fi

# Copy files to the target directory
echo "Copying gateway client files..."
cp gateway_registration.py "$GATEWAY_CLIENT_DIR/"
cp auto_register.py "$GATEWAY_CLIENT_DIR/"
cp gateway_startup.sh "$GATEWAY_CLIENT_DIR/"

# Set proper permissions
chown pi:pi "$GATEWAY_CLIENT_DIR"/*
chmod +x "$GATEWAY_CLIENT_DIR/auto_register.py"
chmod +x "$GATEWAY_CLIENT_DIR/gateway_startup.sh"

# Install systemd service
echo "Installing systemd service..."
cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
chmod 644 "$SYSTEMD_DIR/$SERVICE_FILE"

# Reload systemd and enable the service
echo "Enabling auto-registration service..."
systemctl daemon-reload
systemctl enable gateway-auto-register.service

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The gateway auto-registration service has been installed and enabled."
echo ""
echo "Next steps:"
echo "1. First, register your gateway manually using:"
echo "   cd $GATEWAY_CLIENT_DIR && python3 gateway_registration.py"
echo ""
echo "2. The service will automatically start on next boot, or you can start it manually:"
echo "   sudo systemctl start gateway-auto-register.service"
echo ""
echo "3. Check service status:"
echo "   sudo systemctl status gateway-auto-register.service"
echo ""
echo "4. View logs:"
echo "   sudo journalctl -u gateway-auto-register.service -f"
echo "   tail -f /home/pi/gateway_startup.log"
echo "   tail -f /home/pi/gateway_auto_register.log"
echo ""
echo "5. To disable auto-registration:"
echo "   sudo systemctl disable gateway-auto-register.service"
echo ""

# Install required Python packages if pip is available
if command -v pip3 >/dev/null 2>&1; then
    echo "Installing required Python packages..."
    pip3 install requests
else
    echo "Note: Please install the 'requests' Python package manually:"
    echo "pip3 install requests"
fi

echo "Setup completed successfully!"
