
import os
import re
import yaml
import pytest
from pathlib import Path

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config_validator import SystemConfig

def test_docker_compose_has_all_required_env_vars():
    """
    Ensure docker-compose.central.yml defines all vars used in SystemConfig.
    """
    print("Starting test_docker_compose_has_all_required_env_vars...")
    compose_path = project_root / "docker-compose.central.yml"
    assert compose_path.exists(), f"Could not find {compose_path}"

    with open(compose_path, 'r') as f:
        compose_data = yaml.safe_load(f)

    # Extract all environment variables from ml_worker service
    ml_worker_env = compose_data.get('services', {}).get('ml_worker', {}).get('environment', [])
    
    env_keys = set()
    for entry in ml_worker_env:
        if isinstance(entry, str):
            key = entry.split('=')[0]
            env_keys.add(key)
        elif isinstance(entry, dict):
            # This format is less common in this specific project but good to handle
            env_keys.update(entry.keys())

    # Get required variables from SystemConfig
    # We can't easily introspect the 'required' dict inside from_env, 
    # but we can check the attributes of SystemConfig
    config_fields = SystemConfig.__dataclass_fields__.keys()
    
    # These are variables that we EXPECT to be in the environment
    # Some might have defaults in config_validator.py, but they SHOULD be in compose if they are critical
    
    # This list should match the 'required' dict in SystemConfig.from_env
    required_in_python = [
        'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
        'REDIS_HOST', 'REDIS_PORT', 'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_BUCKET'
    ]
    
    missing_vars = []
    for var in required_in_python:
        if var not in env_keys:
            missing_vars.append(var)
            
    assert not missing_vars, f"Variables missing from docker-compose.central.yml: {', '.join(missing_vars)}"
    print(f"\n✓ All {len(required_in_python)} required variables found in docker-compose.central.yml")

if __name__ == "__main__":
    test_docker_compose_has_all_required_env_vars()
