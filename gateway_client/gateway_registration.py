# gateway_registration.py
import hashlib
import requests
import os
import json

# Replace with your API server's IP or hostname
API_BASE_URL = "http://10.152.208.158:8000/api/v1"
TOKEN_FILE = "/home/pi/.gateway_token"

def save_token(token):
    """Save the registration token to a local file"""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({"token": token}, f)
        os.chmod(TOKEN_FILE, 0o600)  # Secure file permissions
        print(f"Token saved to {TOKEN_FILE}")
    except Exception as e:
        print(f"Error saving token: {str(e)}")

def register_gateway():
    print("=== Gateway Registration ===")
    gateway_name = input("Enter gateway name: ")
    registration_token = input("Enter registration token provided by admin: ")

    # Build the payload as required by your /gateways/register endpoint.
    # Our schema expects { "name": <gateway_name>, "token": <registration_token> }
    payload = {
        "name": gateway_name,
        "token": registration_token
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/gateways/register", json=payload)
        if response.status_code == 200:
            data = response.json()
            print("Gateway registration successful!")
            print("Gateway details:")
            print(f"Name: {data.get('name')}")
            print(f"Status: {data.get('status')}")
            print(f"Last Seen: {data.get('last_seen')}")
            
            # Save the token for future automatic registration
            save_token(registration_token)
        else:
            print(f"Registration failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error during registration: {str(e)}")

if __name__ == "__main__":
    register_gateway()

