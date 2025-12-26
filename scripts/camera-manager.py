"""
Camera Management Helper Script
================================
Command-line interface for managing cameras via the API.
"""

import requests
import json
import sys
from typing import Optional

API_BASE_URL = "http://localhost:8000"


def list_cameras():
    """List all cameras."""
    response = requests.get(f"{API_BASE_URL}/cameras")
    if response.status_code == 200:
        cameras = response.json()
        if not cameras:
            print("No cameras registered.")
            return
        
        print("\n📹 Registered Cameras:")
        print("=" * 80)
        for cam in cameras:
            print(f"ID: {cam['id']}")
            print(f"  Name: {cam['name']}")
            print(f"  Location: {cam['location']}")
            print(f"  IP: {cam['ip']}:{cam['port']}")
            print(f"  Enabled: {'✓' if cam['enabled'] else '✗'}")
            print("-" * 80)
    else:
        print(f"Error: {response.status_code} - {response.text}")


def add_camera(cam_id: str, name: str, location: str, ip: str, port: int = 81):
    """Add a new camera."""
    camera_data = {
        "id": cam_id,
        "name": name,
        "location": location,
        "ip": ip,
        "port": port,
        "enabled": True
    }
    
    response = requests.post(f"{API_BASE_URL}/cameras", json=camera_data)
    if response.status_code == 201:
        print(f"✓ Camera '{name}' added successfully!")
        print(f"  Stream URL: http://{ip}:{port}/stream")
        print(f"  Add this to Kerberos Agent at: http://localhost:8080")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def delete_camera(cam_id: str):
    """Delete a camera."""
    response = requests.delete(f"{API_BASE_URL}/cameras/{cam_id}")
    if response.status_code == 200:
        print(f"✓ Camera '{cam_id}' deleted successfully!")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def get_camera(cam_id: str):
    """Get camera details."""
    response = requests.get(f"{API_BASE_URL}/cameras/{cam_id}")
    if response.status_code == 200:
        cam = response.json()
        print(f"\n📹 Camera: {cam['name']}")
        print("=" * 80)
        print(f"ID: {cam['id']}")
        print(f"Name: {cam['name']}")
        print(f"Location: {cam['location']}")
        print(f"IP: {cam['ip']}:{cam['port']}")
        print(f"Enabled: {'✓' if cam['enabled'] else '✗'}")
        print(f"Stream URL: http://{cam['ip']}:{cam['port']}/stream")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python camera_manager.py list")
        print("  python camera_manager.py add <id> <name> <location> <ip> [port]")
        print("  python camera_manager.py get <id>")
        print("  python camera_manager.py delete <id>")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_cameras()
    elif command == "add":
        if len(sys.argv) < 6:
            print("Error: Missing arguments")
            print("Usage: python camera_manager.py add <id> <name> <location> <ip> [port]")
            return
        cam_id = sys.argv[2]
        name = sys.argv[3]
        location = sys.argv[4]
        ip = sys.argv[5]
        port = int(sys.argv[6]) if len(sys.argv) > 6 else 81
        add_camera(cam_id, name, location, ip, port)
    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: Missing camera ID")
            return
        get_camera(sys.argv[2])
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: Missing camera ID")
            return
        delete_camera(sys.argv[2])
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
