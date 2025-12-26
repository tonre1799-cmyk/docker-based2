#!/usr/bin/env python3
"""
Deployment Script
=================
Unified deployment tool for Central and Edge nodes.
Replaces legacy PowerShell scripts.

Usage:
    python scripts/deploy.py [central|edge] [--build] [--stop] [--camera-id ID]

Examples:
    python scripts/deploy.py central --build
    python scripts/deploy.py edge --camera-id cam-01
"""

import argparse
import subprocess
import sys
import shutil
from pathlib import Path

# Config
ROOT_DIR = Path(__file__).parent.parent.resolve()
DOCKER_COMPOSE_BASE = "docker-compose.yml"
DOCKER_COMPOSE_CENTRAL = "docker-compose.central.yml"
DOCKER_COMPOSE_EDGE = "docker-compose.edge.yml"

def run_command(cmd, cwd=ROOT_DIR, check=True):
    """Run a shell command."""
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=cwd, check=check, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        if check:
            sys.exit(e.returncode)

def check_files():
    """Ensure required files exist."""
    required = [ROOT_DIR / DOCKER_COMPOSE_BASE, ROOT_DIR / ".env"]
    missing = [f for f in required if not f.exists()]
    
    if missing:
        print("ERROR: Missing required files:")
        for f in missing:
            print(f"  - {f}")
        print("\nPlease ensure .env exists in the root directory.")
        sys.exit(1)

def deploy_central(args):
    """Deploy central server stack."""
    print("=== Deploying Central Server ===")
    
    compose_files = ["-f", DOCKER_COMPOSE_BASE, "-f", DOCKER_COMPOSE_CENTRAL]
    
    if args.stop:
        print("Stopping central server...")
        run_command(["docker", "compose"] + compose_files + ["down"])
        return

    if args.build:
        print("Building images...")
        run_command(["docker", "compose"] + compose_files + ["build"])

    print("Starting containers...")
    run_command(["docker", "compose"] + compose_files + ["up", "-d"])
    
    print("\nCentral Server Deployed!")
    print("  Dashboard: http://localhost:8501")
    print("  Vault:     http://localhost:8081")

def deploy_edge(args):
    """Deploy edge agent."""
    print("=== Deploying Edge Agent ===")
    
    compose_files = ["-f", DOCKER_COMPOSE_BASE, "-f", DOCKER_COMPOSE_EDGE]
    
    # Export camera ID for compose
    env_vars = {"CAMERA_ID": args.camera_id or "default_cam"}
    # Note: subprocess environment needs to be handled
    # On Windows/Linux shell=True might handle env vars if passed, 
    # but strictly we should pass `env` param.
    import os
    env = os.environ.copy()
    env.update(env_vars)
    
    # Helper wrapper for env
    def run_cmd_env(cmd):
        print(f"Executing: {' '.join(cmd)} (CAMERA_ID={env_vars['CAMERA_ID']})")
        subprocess.run(cmd, cwd=ROOT_DIR, check=True, shell=True, env=env)

    if args.stop:
        print("Stopping edge agent...")
        run_cmd_env(["docker", "compose"] + compose_files + ["down"])
        return

    if args.build:
         run_cmd_env(["docker", "compose"] + compose_files + ["build"])

    print("Starting containers...")
    run_cmd_env(["docker", "compose"] + compose_files + ["up", "-d"])
    
    print(f"\nEdge Agent Deployed (Camera: {env_vars['CAMERA_ID']})!")
    print("  Agent UI: http://localhost:8080")

def main():
    parser = argparse.ArgumentParser(description="Deployment Tool")
    subparsers = parser.add_subparsers(dest="mode", required=True)
    
    # Central Parser
    central_parser = subparsers.add_parser("central", help="Deploy central server")
    central_parser.add_argument("--build", action="store_true", help="Rebuild images")
    central_parser.add_argument("--stop", action="store_true", help="Stop containers")
    
    # Edge Parser
    edge_parser = subparsers.add_parser("edge", help="Deploy edge agent")
    edge_parser.add_argument("--camera-id", help="Camera Identifier", default="default_cam")
    edge_parser.add_argument("--build", action="store_true", help="Rebuild images")
    edge_parser.add_argument("--stop", action="store_true", help="Stop containers")
    
    args = parser.parse_args()
    
    check_files()
    
    if args.mode == "central":
        deploy_central(args)
    elif args.mode == "edge":
        deploy_edge(args)

if __name__ == "__main__":
    main()
