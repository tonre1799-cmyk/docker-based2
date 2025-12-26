
import os
import yaml
from pathlib import Path

def test_drift():
    print("--- START DRIFT TEST ---")
    project_root = Path(__file__).parent.parent
    compose_path = project_root / "docker-compose.central.yml"
    
    print(f"Reading {compose_path}")
    with open(compose_path, 'r') as f:
        # We need to handle ${VAR} syntax which is NOT valid YAML 1.1/1.2 often 
        # but PyYAML usually handles it as strings if we are lucky.
        # However, it's safer to just read it as text for scanning.
        content = f.read()

    # Look for the ml_worker section
    # Simplified regex-based scanning for the 'environment' section of ml_worker
    ml_worker_start = content.find("ml_worker:")
    if ml_worker_start == -1:
        print("FAIL: Could not find ml_worker in compose file")
        return False

    # Find following 'environment:' block
    env_start = content.find("environment:", ml_worker_start)
    env_end = content.find("command:", env_start)
    if env_end == -1: env_end = content.find("volumes:", env_start)
    
    env_block = content[env_start:env_end]
    print(f"Env block found:\n{env_block}")

    required_vars = [
        'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD',
        'REDIS_HOST', 'REDIS_PORT', 'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_BUCKET'
    ]

    missing = []
    for var in required_vars:
        if var not in env_block:
            missing.append(var)

    if missing:
        print(f"FAIL: Missing vars in ml_worker environment: {', '.join(missing)}")
        return False

    print("SUCCESS: All required variables found in ml_worker env")
    return True

if __name__ == "__main__":
    if test_drift():
        print("--- DRIFT TEST PASSED ---")
        exit(0)
    else:
        print("--- DRIFT TEST FAILED ---")
        exit(1)
