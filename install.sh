#!/bin/bash
set -e

echo "===================================================="
echo "  ML Heatmap & Tracking - Installer (Linux/macOS)"
echo "===================================================="

# 1. Run Verification
python3 scripts/verify_installation.py
if [ $? -ne 0 ]; then
    echo "❌ Pre-flight checks failed. Please fix issues and try again."
    exit 1
fi

# 2. Setup Environment
python3 scripts/setup_env.py

# 3. Pull and Start
echo "Pulling Docker images..."
docker-compose pull

echo "Starting services in detached mode..."
docker-compose -f docker-compose.yml -f docker-compose.central.yml up -d

echo "===================================================="
echo "  🚀 INSTALLATION COMPLETE"
echo "===================================================="
echo "Access the dashboard at: http://localhost:8501"
echo "Access Kerberos Vault at: http://localhost:8081"
echo "Check service status with: docker-compose ps"
