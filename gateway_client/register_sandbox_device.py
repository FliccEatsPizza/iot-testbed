import requests
import json
import os

SERVER_URL = os.getenv("SERVER_URL", "http://10.152.208.158:8000")
GATEWAY_ID = int(os.getenv("GATEWAY_ID", "1"))

def register_device(name: str, device_type: str, gateway_id: int):
    url = f"{SERVER_URL}/api/v1/devices/"
    payload = {
        "name": name,
        "gateway_id": gateway_id,
        "device_type": device_type
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully registered device '{name}' (ID: {data.get('id')}, Type: {device_type})")
            return data
        else:
            print(f"❌ Failed to register '{name}': {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🔴 Connection error: {e}")
    return None

def main():
    print("=" * 60)
    print(" IoT Testbed — Device Registration (Sandbox & Border Router)")
    print("=" * 60)
    
    print("\nSelect action:")
    print("1. Register Virtual Pi Sandbox Slots (e.g. pi-sandbox-1, pi-sandbox-2)")
    print("2. Register RPL Border Router (e.g. pi-border-router)")
    print("3. Register Standard Physical Node")
    
    choice = input("\nEnter choice [1-3] (default 1): ").strip() or "1"
    
    if choice == "1":
        count_str = input("How many sandbox slots to register? (e.g. 2): ").strip() or "2"
        count = int(count_str)
        prefix = input("Device name prefix (default 'pi-sandbox'): ").strip() or "pi-sandbox"
        for i in range(1, count + 1):
            name = f"{prefix}-{i}"
            register_device(name=name, device_type="sandbox", gateway_id=GATEWAY_ID)
            
    elif choice == "2":
        name = input("Border Router device name (default 'pi-border-router'): ").strip() or "pi-border-router"
        register_device(name=name, device_type="border_router", gateway_id=GATEWAY_ID)
        
    elif choice == "3":
        name = input("Physical device name: ").strip()
        if name:
            register_device(name=name, device_type="physical", gateway_id=GATEWAY_ID)
        else:
            print("Device name cannot be empty.")

if __name__ == "__main__":
    main()
