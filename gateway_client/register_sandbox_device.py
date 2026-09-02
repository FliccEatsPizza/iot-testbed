import requests
import json
from config import SERVER_URL, GATEWAY_ID

def register_device(name: str, device_type: str, gateway_id: int):
    url = f"{SERVER_URL}/api/v1/devices/"
    payload = {
        "name": name,
        "gateway_id": gateway_id,
        "device_type": device_type
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully registered sandbox slot '{name}' (ID: {data.get('id')})")
            return data
        else:
            print(f"❌ Failed to register '{name}': {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🔴 Connection error: {e}")
    return None

def main():
    print("=" * 60)
    print(" IoT Testbed — Register Virtual Pi Sandbox Slots (Docker)")
    print("=" * 60)
    print("ℹ️  Note: For physical USB boards (Physical Nodes & Border Routers),")
    print("   please use 'gateway_add_device.py' to map their serial ports.\n")
    
    count_str = input("How many sandbox slots to register? (default 2): ").strip() or "2"
    try:
        count = int(count_str)
    except ValueError:
        print("❌ Invalid number. Exiting.")
        return

    prefix = input("Device name prefix (default 'pi-sandbox'): ").strip() or "pi-sandbox"
    
    print(f"\nRegistering {count} virtual sandbox slot(s)...")
    for i in range(1, count + 1):
        name = f"{prefix}-{i}"
        register_device(name=name, device_type="sandbox", gateway_id=GATEWAY_ID)
    
    print("\n🎉 Sandbox slots registered successfully! They will appear on your web dashboard.\n")

if __name__ == "__main__":
    main()
