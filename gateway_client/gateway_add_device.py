import os
import sqlite3
import json
from datetime import datetime
import requests
import serial.tools.list_ports

# Configuration
from config import SERVER_URL, API_BASE_URL, GATEWAY_ID
DEVICE_ENDPOINT = f"{API_BASE_URL}/devices"
DB_PATH = "gateway_devices.db"  # SQLite database file

def get_device_port(device_id: int) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT port FROM devices WHERE device_id = ?", (device_id,))
        result = cur.fetchone()
        return result[0] if result else None

def get_device_by_port(port: str):
    """Retrieve existing mapping for a given port if any"""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT device_id, name FROM devices WHERE port = ?", (port,))
        return cur.fetchone()

def initialize_database():
    """Create database and table if they don't exist"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            port TEXT NOT NULL,
            description TEXT,
            gateway_id INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

def discover_connected_devices():
    """Discover connected serial devices using pyserial"""
    ports = serial.tools.list_ports.comports()
    device_list = []
    for port in ports:
        existing = get_device_by_port(port.device)
        device_list.append({
            "port": port.device,
            "description": port.description,
            "hwid": port.hwid,
            "existing": existing  # (device_id, name) or None
        })
    return device_list

def select_device(devices):
    """Display devices and prompt user selection"""
    if not devices:
        print("❌ No connected serial devices found.")
        exit(1)
        
    print("\nAvailable Serial Ports:")
    for idx, dev in enumerate(devices, start=1):
        status_tag = f" 🟢 [Registered as: '{dev['existing'][1]}' (ID: {dev['existing'][0]})]" if dev.get("existing") else " ⚪ [Not registered]"
        print(f"  {idx}. {dev['port']} - {dev['description']}{status_tag}")
    
    try:
        choice = input("\nSelect device by number [1-{}]: ".format(len(devices))).strip()
        index = int(choice) - 1
        if 0 <= index < len(devices):
            return devices[index]
        else:
            print("❌ Invalid number selected. Exiting.")
            exit(1)
    except (ValueError, IndexError):
        print("❌ Invalid input. Exiting.")
        exit(1)

def add_device_to_server(device_name):
    """Register device with the central server""" 
    payload = {
        "name": device_name,
        "gateway_id": GATEWAY_ID
    }
    try:
        response = requests.post(DEVICE_ENDPOINT, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Server error ({response.status_code}): {response.text}")
            exit(1)
    except requests.exceptions.RequestException as e:
        print(f"🔴 Connection error: Cannot reach server at {DEVICE_ENDPOINT}. {str(e)}")
        exit(1)

def store_device_mapping(server_data, port_info):
    """Store or update device-port mapping in SQLite database"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Clean up any existing mapping for this port or device_id
            conn.execute("DELETE FROM devices WHERE port = ? OR device_id = ?", (port_info['port'], server_data['id']))
            conn.execute("""
            INSERT INTO devices (device_id, name, port, description, gateway_id)
            VALUES (?, ?, ?, ?, ?)
            """, (
                server_data['id'],
                server_data['name'],
                port_info['port'],
                port_info['description'],
                GATEWAY_ID
            ))
            conn.commit()
        print(f"✅ Device '{server_data['name']}' (ID: {server_data['id']}) mapped to {port_info['port']}")
    except sqlite3.Error as e:
        print(f"🔴 Database error: {str(e)}")
        exit(1)

def main():
    initialize_database()
    
    print("=" * 60)
    print(" IoT Testbed — Add / Map Physical USB Device")
    print("=" * 60)

    # Device discovery and selection
    devices = discover_connected_devices()
    selected = select_device(devices)
    
    # Check if port is already registered
    if selected.get("existing"):
        existing_id, existing_name = selected["existing"]
        print(f"\n⚠️  Warning: Port {selected['port']} is ALREADY mapped to device '{existing_name}' (ID: {existing_id}).")
        confirm = input("Do you want to re-register / overwrite this port with a new device? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Operation cancelled. Keeping existing device mapping.")
            exit(0)

    print(f"\nSelected: {selected['port']} ({selected['description']})")
    
    # Get device name from user
    name = input("Enter new device name (e.g. nrf52-node-2): ").strip()
    if not name:
        print("❌ Device name cannot be empty. Exiting.")
        exit(1)
    
    # Server registration
    server_response = add_device_to_server(name)
    
    # Local storage
    store_device_mapping(server_response, selected)
    
    print(f"🎉 Device '{name}' successfully registered and ready for jobs!\n")

if __name__ == "__main__":
    main()
