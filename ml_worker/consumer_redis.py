"""
Redis Queue Consumer for ML Worker
===================================
Consumes video processing tasks from Redis queue.
Downloads videos from Minio S3, processes them, and saves results to PostgreSQL.
Supports horizontal scaling - run multiple instances for parallel processing.
"""

import os
import time
import logging
import redis
import json
import sys
import gc
import psutil
from pathlib import Path
from minio import Minio
from io import BytesIO
import tempfile
import http.server
import socketserver
import threading

# Import existing modules
import signal
import threading
from core.config_manager import get_config
from infrastructure.repositories import get_repository
from services.processing_service import ProcessingService, CameraInfo
from ml_worker.config_loader import load_camera_config, load_models_config
from ml_worker.common import VideoHandler
from ml_worker.video_preprocessor import VideoPreprocessor

# Configuration
# Load centralized configuration
try:
    config = get_config()
except Exception as e:
    print(f"CRITICAL: Configuration load failed: {e}")
    exit(1)

REDIS_HOST = config.redis_host
REDIS_PORT = config.redis_port
TASK_QUEUE = "ml_processing_queue"
DLQ_QUEUE = "ml_processing_dlq"
MAX_RETRIES = 3

MINIO_ENDPOINT = config.minio_endpoint
MINIO_ACCESS_KEY = config.minio_access_key
MINIO_SECRET_KEY = config.minio_secret_key
MINIO_BUCKET = config.minio_bucket

DB_PATH = config.db_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize# Initialize Redis connection pool
redis_pool = redis.ConnectionPool(
    host=config.redis_host, 
    port=config.redis_port, 
    decode_responses=True,
    max_connections=10  # ML workers are processing heavy, don't need many connections
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Configure MinIO
s3_client = Minio(
    config.minio_endpoint,
    access_key=config.minio_access_key,
    secret_key=config.minio_secret_key.get_secret_value(),
    secure=config.minio_secure
)

def start_health_server(repo, port=8080):
    """Start a lightweight health check server in a background thread."""
    class HealthHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/health':
                # Check dependencies
                status = "healthy"
                deps = {"redis": "connected", "database": "connected"}
                
                try:
                    redis_client.ping()
                except Exception as e:
                    status = "unhealthy"
                    deps["redis"] = f"disconnected: {str(e)}"
                
                try:
                    if not repo.health_check():
                        status = "unhealthy"
                        deps["database"] = "disconnected"
                except Exception as e:
                    status = "unhealthy"
                    deps["database"] = f"error: {str(e)}"
                
                self.send_response(200 if status == "healthy" else 500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": status,
                    "service": "ml-worker-redis",
                    "dependencies": deps,
                    "timestamp": datetime.now().isoformat()
                }
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            return

    def run_server():
        try:
            with socketserver.TCPServer(("", port), HealthHandler) as httpd:
                logger.info(f"Health check server started on port {port}")
                httpd.serve_forever()
        except Exception as e:
            logger.error(f"Health server failed: {e}")

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


def download_video_from_s3(s3_key: str, bucket: str = MINIO_BUCKET) -> Path:
    """
    Download video from Minio S3 to temporary file.
    
    Args:
        s3_key: S3 object key
        bucket: S3 bucket name
        
    Returns:
        Path to downloaded temporary file
    """
    try:
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        temp_path = Path(temp_file.name)
        
        # Download from S3
        logger.info(f"Downloading {s3_key} from S3...")
        minio_client.fget_object(bucket, s3_key, str(temp_path))
        logger.info(f"Downloaded to {temp_path}")
        
        return temp_path
    except Exception as e:
        logger.error(f"Error downloading from S3: {e}")
        raise


from datetime import datetime

def process_with_retry(task_json: str, handler: VideoHandler) -> None:
    """
    Process a single task from the queue with retry logic and DLQ.
    
    Args:
        task_json: JSON string of the task from Redis
        handler: VideoHandler instance
    """
    try:
        task = json.loads(task_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid task JSON: {e}")
        redis_client.rpush(DLQ_QUEUE, task_json)
        return

    camera_id = task.get("camera_id", "unknown")
    tenant_id = task.get("tenant_id", "default")
    filename = task.get("filename", "unknown")
    s3_key = task.get("s3_key", "")
    bucket = task.get("bucket", f"{MINIO_BUCKET}-{tenant_id}" if tenant_id != "default" else MINIO_BUCKET)
    retry_count = task.get('retry_count', 0)
    
    logger.info(f"Processing task: {filename} (Tenant: {tenant_id}, Camera: {camera_id}, Attempt: {retry_count+1}/{MAX_RETRIES+1})")
    
    try:
        # Download video from S3
        video_path = download_video_from_s3(s3_key, bucket)
        optimized_path = None
        
        try:
            # Optimize video before ML processing
            optimized_path = VideoPreprocessor.optimize_for_ml(video_path)
            
            # Process the video (pass tenant_id)
            handler.process_file(optimized_path, tenant_id=tenant_id)
            logger.info(f"✓ Task completed: {filename}")
        finally:
            # Clean up temporary files
            if video_path.exists():
                video_path.unlink()
                logger.debug(f"Cleaned up original temp file: {video_path}")
            if optimized_path and optimized_path.exists() and optimized_path != video_path:
                optimized_path.unlink()
                logger.debug(f"Cleaned up optimized temp file: {optimized_path}")
        
    except Exception as e:
        logger.error(f"Task processing failed for {filename}: {e}")
        
        if retry_count < MAX_RETRIES:
            # Retry with exponential backoff
            task['retry_count'] = retry_count + 1
            task['last_error'] = str(e)
            task['last_attempt'] = datetime.now().isoformat()
            
            # Note: In a production system, we might use a separate delayed queue 
            # or a more sophisticated scheduler instead of time.sleep in the worker.
            # But for this implementation, we follow the requested pattern.
            delay = 2 ** retry_count 
            logger.info(f"Task requeued. Waiting {delay}s before retry...")
            time.sleep(delay)
            
            redis_client.rpush(TASK_QUEUE, json.dumps(task))
            logger.info(f"Task requeued (attempt {task['retry_count']}/{MAX_RETRIES})")
        else:
            # Move to DLQ
            task['last_error'] = str(e)
            task['failed_at'] = datetime.now().isoformat()
            redis_client.rpush(DLQ_QUEUE, json.dumps(task))
            logger.error(f"Task moved to DLQ ({DLQ_QUEUE}) after {MAX_RETRIES+1} failures")


def main():
    """Main entry point for Redis queue consumer."""
    logger.info("=" * 50)
    logger.info("  ML Worker (Redis Queue Mode) Started")
    logger.info("=" * 50)
    logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"Queue: {TASK_QUEUE}")
    
    # Initialize repository
    repo = get_repository()
    repo.init_schema()
    
    # Initialize Model Registry
    from core.registry.model_registry import ModelRegistry
    from ml_worker.models import HeatmapModel, ObjectTrackingModel, PersonDetectionModel
    
    registry = ModelRegistry()
    registry.register_class('heatmap', HeatmapModel)
    registry.register_class('tracking', ObjectTrackingModel)
    registry.register_class('person_detection', PersonDetectionModel)
    registry.load_from_config(config.config_dir / "models.yml")
    
    # Initialize Processing Service
    processing_service = ProcessingService(
        registry=registry,
        analytics_repo=repo,
        heatmap_repo=repo,
        tracking_repo=repo,
        person_detection_repo=repo
    )
    
    # Create video handler
    stop_event = threading.Event()
    handler = VideoHandler(processing_service, repo, stop_event=stop_event)
    
    # Start health check server
    start_health_server(repo, port=8080)

    logger.info("Waiting for tasks from Redis queue...")
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, stopping...")
        stop_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Main processing loop
    while not stop_event.is_set():
        try:
            # Blocking pop from Redis queue (timeout 2 seconds to allow shutdown check)
            result = redis_client.blpop(TASK_QUEUE, timeout=2)
            
            if result:
                _, task_json = result
                task = json.loads(task_json)
                
                # ... (Assuming download logic is inside process_with_retry or we add it here)
                # Actually, I should check where the file is downloaded.
                # The provided example shows it in process_with_retry.
                
                process_with_retry(task_json, handler)
                
                # Force garbage collection and log memory
                gc.collect()
                try:
                    process = psutil.Process()
                    mem_mb = process.memory_info().rss / 1024 / 1024
                    logger.info(f"Memory usage: {mem_mb:.1f} MB")
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            if not stop_event.is_set():
                time.sleep(5) 
            
    logger.info("Cleaning up resources...")
    try:
        redis_client.close()
    except:
        pass
    logger.info("Graceful shutdown complete.")


if __name__ == "__main__":
    main()
