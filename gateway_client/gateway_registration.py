# gateway_registration.py
import hashlib
import requests
import os
import json
import sys

# Configuration
from config import API_BASE_URL, SERVER_HOST, SERVER_PORT
TOKEN_FILE = "/home/pi/.gateway_token"

def save_token(token):
    """Save the registration token to a local file"""
    try:
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, 'w') as f:
            json.dump({"token": token}, f)
        os.chmod(TOKEN_FILE, 0o600)  # Secure file permissions
        print(f"✅ Token saved to {TOKEN_FILE}")
    except Exception as e:
        print(f"⚠️ Error saving token: {str(e)}")

def save_gateway_id(gateway_id):
    """Save the gateway ID to gateway_id.txt so gateway_client.py knows its ID"""
    try:
        id_file = os.path.join(os.path.dirname(__file__), "gateway_id.txt")
        with open(id_file, "w") as f:
            f.write(str(gateway_id))
        print(f"✅ Gateway ID ({gateway_id}) saved to {id_file}")
    except Exception as e:
        print(f"⚠️ Error saving gateway ID: {str(e)}")

def register_gateway():
    print("==========================================")
    print("       IoT Testbed Gateway Registration   ")
    print("==========================================")
    print(f"Target Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print("------------------------------------------")
    
    gateway_name = input("Enter gateway name: ").strip()
    if not gateway_name:
        print("❌ Error: Gateway name cannot be empty.")
        sys.exit(1)
        
    registration_token = input("Enter registration token provided by admin: ").strip()
    if not registration_token:
        print("❌ Error: Token cannot be empty.")
        sys.exit(1)

    payload = {
        "name": gateway_name,
        "token": registration_token
    }
    
    register_url = f"{API_BASE_URL}/gateways/register"
    print(f"\n⏳ Connecting to {register_url} ...")
    
    try:
        response = requests.post(register_url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            gateway_id = data.get('id')
            print("\n🎉 Gateway registration successful!")
            print("------------------------------------------")
            print(f"  Gateway ID : {gateway_id}")
            print(f"  Name       : {data.get('name')}")
            print(f"  Status     : {data.get('status')}")
            print(f"  Last Seen  : {data.get('last_seen')}")
            print("------------------------------------------")
            
            # Save token and gateway ID locally
            save_token(registration_token)
            if gateway_id is not None:
                save_gateway_id(gateway_id)
                
            print("\n🚀 You can now start the gateway client:")
            print(f"   GATEWAY_ID={gateway_id} python3 gateway_client.py\n")
        elif response.status_code == 404:
            err_msg = "Unknown error"
            try:
                err_msg = response.json().get("detail", response.text)
            except Exception:
                err_msg = response.text
            print(f"\n❌ Registration rejected by server (404): {err_msg}")
            print("   Please check the gateway name and token in your dashboard.")
        else:
            print(f"\n❌ Registration failed: HTTP {response.status_code}")
            print(f"   Details: {response.text}")
            
    except requests.exceptions.ConnectTimeout:
        print(f"\n❌ Connection timed out to {SERVER_HOST}:{SERVER_PORT} after 10 seconds.")
        print(f"   Troubleshooting:")
        print(f"   1. Confirm your laptop's current Wi-Fi IP address (ipconfig).")
        print(f"   2. Update SERVER_HOST in config.py if the laptop IP changed.")
        print(f"   3. Verify the backend is running on the laptop (port {SERVER_PORT}).")
    except requests.exceptions.ConnectionError as ce:
        print(f"\n❌ Cannot connect to server at {register_url}")
        print(f"   Details: {ce}")
        print(f"   Make sure the backend is running on {SERVER_HOST}:{SERVER_PORT}.")
    except Exception as e:
        print(f"\n❌ Unexpected error during registration: {str(e)}")

if __name__ == "__main__":
    register_gateway()
