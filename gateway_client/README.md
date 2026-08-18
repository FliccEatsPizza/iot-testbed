# Gateway Client - Automatic Registration System

This directory contains the client-side scripts for Raspberry Pi gateway automatic registration.

## Overview

The system implements automatic gateway registration that eliminates the need for manual intervention when a Raspberry Pi reconnects to the network. The flow works as follows:

1. **Initial Setup**: Manual registration saves a token locally
2. **Automatic Registration**: On boot, the Pi uses the saved token to register automatically
3. **Fallback**: If token is invalid/expired, manual registration is required

## Files Description

### Core Scripts

- **`gateway_registration.py`** - Manual registration script (enhanced to save tokens)
- **`auto_register.py`** - Automatic token verification and registration
- **`gateway_startup.sh`** - Bash script that runs on startup
- **`gateway-auto-register.service`** - Systemd service file
- **`setup_auto_registration.sh`** - Setup script for installation

## Installation on Raspberry Pi

### 1. Copy Files to Raspberry Pi

Copy all files from this directory to your Raspberry Pi.

### 2. Run Setup Script

```bash
# Make setup script executable
chmod +x setup_auto_registration.sh

# Run setup (requires root for systemd service)
sudo ./setup_auto_registration.sh
```

### 3. Initial Manual Registration

```bash
cd /home/pi/gateway_client
python3 gateway_registration.py
```

This will:
- Prompt for gateway name and registration token
- Register with the server
- Save the token locally for future automatic registration

## How It Works

### Automatic Registration Flow

1. **Boot Process**: Systemd service starts `gateway_startup.sh`
2. **Network Wait**: Script waits for network connectivity
3. **Token Check**: `auto_register.py` checks for saved token
4. **Server Verification**: Sends token to `/api/v1/gateways/verify-token` endpoint
5. **Registration**: If valid, gateway is automatically registered

### Server-Side Changes

The server now includes:
- **New Endpoint**: `POST /api/v1/gateways/verify-token`
- **Enhanced Service**: `GatewayService.verify_token_and_register()`
- **New Schema**: `GatewayTokenVerify`

## Configuration

### API Server URL

Update the `API_BASE_URL` in both scripts:

```python
# In gateway_registration.py and auto_register.py
API_BASE_URL = "http://YOUR_SERVER_IP:8000/api/v1"
```

### File Locations

- **Token Storage**: `/home/pi/.gateway_token`
- **Logs**: 
  - `/home/pi/gateway_startup.log`
  - `/home/pi/gateway_auto_register.log`
- **Scripts**: `/home/pi/gateway_client/`

## Service Management

### Check Service Status
```bash
sudo systemctl status gateway-auto-register.service
```

### View Logs
```bash
# Systemd logs
sudo journalctl -u gateway-auto-register.service -f

# Application logs
tail -f /home/pi/gateway_startup.log
tail -f /home/pi/gateway_auto_register.log
```

### Manual Service Control
```bash
# Start service manually
sudo systemctl start gateway-auto-register.service

# Stop service
sudo systemctl stop gateway-auto-register.service

# Disable auto-start
sudo systemctl disable gateway-auto-register.service

# Enable auto-start
sudo systemctl enable gateway-auto-register.service
```

## Troubleshooting

### Common Issues

1. **Network Connectivity**
   - Service waits up to 5 minutes for network
   - Check network configuration and DNS

2. **Token Issues**
   - Invalid token: Re-run manual registration
   - Missing token: Run initial manual registration

3. **Permission Issues**
   - Ensure files are owned by `pi` user
   - Check file permissions (scripts should be executable)

4. **Server Connection**
   - Verify server IP and port in configuration
   - Check firewall settings
   - Ensure server is running

### Log Analysis

Check logs for specific error messages:

```bash
# Recent service logs
sudo journalctl -u gateway-auto-register.service --since "1 hour ago"

# Python script logs
grep "ERROR" /home/pi/gateway_auto_register.log
```

## Security Considerations

- Token file has restricted permissions (600)
- Service runs as `pi` user (not root)
- Tokens are stored locally and transmitted securely
- Failed attempts are logged for monitoring

## Manual Operations

### Re-register Gateway
```bash
cd /home/pi/gateway_client
python3 gateway_registration.py
```

### Test Auto-Registration
```bash
cd /home/pi/gateway_client
python3 auto_register.py
```

### Remove Saved Token
```bash
rm /home/pi/.gateway_token
```

## Dependencies

- Python 3
- `requests` library (`pip3 install requests`)
- systemd (for service management)
- Network connectivity to server
