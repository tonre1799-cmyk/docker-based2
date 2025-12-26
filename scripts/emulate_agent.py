"""
Kerberos Agent Emulator
=======================
Simulates an Agent uploading a video and triggering the pipeline.

Workflow:
1. Connects to Minio S3.
2. Uploads a local MP4 file to the 'recordings' bucket.
3. Sends a Webhook to the Dispatcher service with metadata.

Usage:
    python emulate_agent.py --file path/to/video.mp4 --camera cam-integration-01
"""

import argparse
import logging
import time
import os
import requests
import mimetypes
from pathlib import Path
from minio import Minio
from datetime import datetime

# Configuration
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "recordings")
DISPATCHER_URL = os.environ.get("DISPATCHER_URL", "http://localhost:5000/webhook")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("emulator")

def setup_minio():
    """Initialize Minio client and ensure bucket exists."""
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    if not client.bucket_exists(MINIO_BUCKET):
        logger.info(f"Creating bucket: {MINIO_BUCKET}")
        client.make_bucket(MINIO_BUCKET)
    
    return client

def upload_video(client, file_path, camera_id):
    """Upload video to S3."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")
    
    # Generate S3 key: <camera_id>/YYYY-MM-DD/<timestamp>.mp4
    timestamp = int(time.time())
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{timestamp}_{file_path.name}"
    s3_key = f"{camera_id}/{date_str}/{filename}"
    
    logger.info(f"Uploading {file_path.name} to {MINIO_BUCKET}/{s3_key}...")
    
    try:
        with open(file_path, "rb") as file_data:
            file_stat = os.stat(file_path)
            client.put_object(
                MINIO_BUCKET,
                s3_key,
                file_data,
                file_stat.st_size,
                content_type="video/mp4"
            )
        logger.info("Upload complete")
        return s3_key, filename
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise

def trigger_webhook(camera_id, s3_key, filename):
    """Send webhook to Dispatcher."""
    payload = {
        "camera_id": camera_id,
        "cameraId": camera_id,  # Supports both naming conventions
        "key": s3_key,
        "filename": filename,
        "bucket": MINIO_BUCKET,
        "timestamp": int(time.time()),
        "microseconds": 0
    }
    
    logger.info(f"Sending webhook to {DISPATCHER_URL}...")
    try:
        response = requests.post(DISPATCHER_URL, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f"Webhook success: {response.json()}")
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Emulate Agent Upload")
    parser.add_argument("--file", required=True, help="Path to video file")
    parser.add_argument("--camera", default="test-cam-01", help="Camera ID")
    args = parser.parse_args()
    
    try:
        # 1. Setup Minio
        client = setup_minio()
        
        # 2. Upload Video
        s3_key, filename = upload_video(client, args.file, args.camera)
        
        # 3. Trigger Pipeline
        trigger_webhook(args.camera, s3_key, filename)
        
        logger.info("Emulation sequence completed successfully")
        
    except Exception as e:
        logger.error(f"Emulation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
