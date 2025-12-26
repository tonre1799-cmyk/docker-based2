#!/usr/bin/env python3
"""
Validate configuration completeness before deployment.
Usage: python scripts/validate_config.py
"""

import sys
import yaml
from pathlib import Path
from ipaddress import IPv4Address
import os

def validate_cameras_config(config_path: Path) -> list[str]:
    """Validate cameras.yml."""
    errors = []
    
    if not config_path.exists():
        return [f"Config file not found: {config_path}"]
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    if 'cameras' not in data:
        return ["Missing 'cameras' key in config"]
    
    for i, cam in enumerate(data['cameras']):
        # Required fields
        for field in ['id', 'name', 'location', 'ip', 'port']:
            if field not in cam:
                errors.append(f"Camera {i}: missing '{field}'")
        
        # Validate IP (if it looks like an IP, not a hostname)
        ip_val = cam.get('ip')
        if ip_val:
            try:
                # If it contains dots, assume it's an IP
                if '.' in ip_val and not any(c.isalpha() for c in ip_val):
                    IPv4Address(ip_val)
            except ValueError:
                errors.append(f"Camera {i}: invalid IP address: {ip_val}")
        
        # Validate port
        port_val = cam.get('port')
        if port_val is not None:
            try:
                if not 1 <= int(port_val) <= 65535:
                    errors.append(f"Camera {i}: invalid port: {port_val}")
            except (ValueError, TypeError):
                errors.append(f"Camera {i}: port must be an integer: {port_val}")
    
    return errors

def validate_models_config(config_path: Path) -> list[str]:
    """Validate models.yml."""
    errors = []
    
    if not config_path.exists():
        return [f"Config file not found: {config_path}"]
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    if 'models' not in data:
        return ["Missing 'models' key in config"]
    
    for i, model in enumerate(data['models']):
        if 'id' not in model:
            errors.append(f"Model {i}: missing 'id'")
        if 'enabled' not in model:
            errors.append(f"Model {i}: missing 'enabled'")
    
    return errors

def main():
    """Run all validations."""
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    
    all_errors = []
    
    # Validate cameras
    errors = validate_cameras_config(config_dir / "cameras.yml")
    if errors:
        all_errors.extend([f"cameras.yml: {e}" for e in errors])
    
    errors = validate_models_config(config_dir / "models.yml")
    if errors:
        all_errors.extend([f"models.yml: {e}" for e in errors])
    
    # Validate environment variables
    errors = validate_env_vars()
    if errors:
        all_errors.extend([f"env: {e}" for e in errors])
    
    # Report
    if all_errors:
        print("❌ Configuration validation failed:\n")
        for error in all_errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ Configuration validation passed")

if __name__ == "__main__":
    main()
