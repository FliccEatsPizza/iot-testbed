#!/usr/bin/env python3
# auto_register.py
import requests
import json
import os
import sys
import time
import logging

# Configuration
API_BASE_URL = "http://10.152.208.158:8000/api/v1"
TOKEN_FILE = "/home/pi/.gateway_token"
LOG_FILE = "/home/pi/gateway_auto_register.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def load_token():
    """Load the registration token from local file"""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                return data.get("token")
        return None
    except Exception as e:
        logging.error(f"Error loading token: {str(e)}")
        return None

def verify_token_with_server(token):
    """Verify token with server and register gateway automatically"""
    try:
        payload = {"token": token}
        response = requests.post(f"{API_BASE_URL}/gateways/verify-token", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logging.info("Gateway auto-registration successful!")
            logging.info(f"Gateway Name: {data.get('name')}")
            logging.info(f"Status: {data.get('status')}")
            logging.info(f"Last Seen: {data.get('last_seen')}")
            return True
        elif response.status_code == 401:
            logging.warning("Token verification failed: Invalid or expired token")
            return False
        else:
            logging.error(f"Token verification failed: {response.status_code} {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        logging.error("Cannot connect to server. Server may be down or network issue.")
        return False
    except requests.exceptions.Timeout:
        logging.error("Request timeout. Server may be slow to respond.")
        return False
    except Exception as e:
        logging.error(f"Error during token verification: {str(e)}")
        return False

def wait_for_network(max_attempts=30, delay=2):
    """Wait for network connectivity"""
    for attempt in range(max_attempts):
        try:
            # Try to reach the server
            response = requests.get(f"{API_BASE_URL.split('/api')[0]}/docs", timeout=5)
            if response.status_code in [200, 404]:  # Server is reachable
                logging.info("Network connectivity established")
                return True
        except:
            pass
        
        logging.info(f"Waiting for network connectivity... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(delay)
    
    logging.error("Network connectivity timeout")
    return False

def main():
    logging.info("=== Gateway Auto-Registration Started ===")
    
    # Wait for network connectivity
    if not wait_for_network():
        logging.error("Failed to establish network connectivity. Exiting.")
        sys.exit(1)
    
    # Load existing token
    token = load_token()
    
    if not token:
        logging.warning("No saved token found. Manual registration required.")
        logging.info("Please run gateway_registration.py to register this gateway manually.")
        sys.exit(1)
    
    logging.info("Found saved token. Attempting automatic registration...")
    
    # Verify token with server
    if verify_token_with_server(token):
        logging.info("Gateway successfully registered automatically!")
        sys.exit(0)
    else:
        logging.error("Automatic registration failed. Manual registration may be required.")
        logging.info("The token may be invalid or expired. Please run gateway_registration.py again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
