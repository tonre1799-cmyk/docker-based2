import os
import sys
import shutil
import socket
import platform
import subprocess
from pathlib import Path

def check_port(port):
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def check_command(cmd):
    """Check if a command is available in the path."""
    return shutil.which(cmd) is not None

def get_disk_free(path="."):
    """Get free disk space in GB."""
    total, used, free = shutil.disk_usage(path)
    return free / (1024**3)

def verify():
    print("=" * 50)
    print("  ML Heatmap & Tracking - Installation Verifier")
    print("=" * 50)
    
    all_passed = True
    
    # 1. System Info
    print(f"\n[1] System Information:")
    print(f"    OS: {platform.system()} {platform.release()}")
    print(f"    Python: {sys.version.split()[0]}")
    
    # 2. Dependencies
    print(f"\n[2] Required Tools:")
    tools = ["docker", "docker-compose"]
    for tool in tools:
        if check_command(tool):
            print(f"    ✅ {tool}: Installed")
        else:
            print(f"    ❌ {tool}: NOT FOUND")
            all_passed = False

    # 3. Port Availability
    print(f"\n[3] Port Availability:")
    ports = {
        5000: "Dispatcher",
        8000: "Camera API",
        8501: "Dashboard",
        3000: "Grafana",
        9000: "MinIO S3",
        9001: "MinIO UI",
        16686: "Jaeger UI"
    }
    for port, name in ports.items():
        if check_port(port):
            print(f"    ✅ Port {port} ({name}): Available")
        else:
            print(f"    ❌ Port {port} ({name}): IN USE")
            all_passed = False

    # 4. Disk Space
    print(f"\n[4] Disk Space:")
    free_gb = get_disk_free()
    if free_gb > 10:
        print(f"    ✅ Free Space: {free_gb:.2f} GB (Requirement: >10GB)")
    else:
        print(f"    ⚠️  Free Space: {free_gb:.2f} GB (Low space warning)")

    # 5. Config Check
    print(f"\n[5] Configuration:")
    if Path(".env").exists():
        print("    ✅ .env file: Found")
    else:
        print("    ⚠️  .env file: NOT FOUND (Will be created from .env.example)")

    print("\n" + "=" * 50)
    if all_passed:
        print("  ✅ VERIFICATION SUCCESSFUL: Environment is ready.")
        return True
    else:
        print("  ❌ VERIFICATION FAILED: Please resolve the issues above.")
        return False

if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
