import os
import secrets
import string
from pathlib import Path

def generate_password(length=24):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def setup_env():
    root_dir = Path(__file__).parent.parent
    example_file = root_dir / ".env.example"
    env_file = root_dir / ".env"
    
    if env_file.exists():
        print(f"✅ .env file already exists at {env_file}")
        return

    if not example_file.exists():
        print(f"❌ .env.example not found at {example_file}")
        return

    print("Generating .env with secure random passwords...")
    
    with open(example_file, 'r') as f:
        content = f.read()
    
    # Replace placeholders with random values
    content = content.replace("CHANGE_ME_RANDOM_KEY", secrets.token_hex(32))
    
    # Replace all password placeholders
    while "CHANGE_ME_RANDOM_PASSWORD" in content:
        content = content.replace("CHANGE_ME_RANDOM_PASSWORD", generate_password(), 1)
        
    with open(env_file, 'w') as f:
        f.write(content)
        
    print(f"✅ Secure .env file created at {env_file}")
    print("⚠️  Remember to update CAMERA_STREAM_URL if needed.")

if __name__ == "__main__":
    setup_env()
