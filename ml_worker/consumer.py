"""
ML Video Consumer
=================
Watches for new MP4 files in the recordings directory,
processes them with ML, and saves results to SQLite.
Supports multi-camera setups with camera metadata from cameras.yml.
Runs multiple ML models per video (heatmap, tracking, etc.).

Model Chaining:
- PersonDetectionModel runs first to get human positions
- HeatmapModel uses person detections for Sony AITRIOS heatmap
- Other models run independently
"""

import os
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
import signal
import threading
from watchdog.events import FileSystemEventHandler
from infrastructure.repositories import get_repository
from services.processing_service import ProcessingService, CameraInfo
from core.config_manager import get_config
from ml_worker.config_loader import load_camera_config, load_models_config
from ml_worker.common import VideoHandler, get_camera_info

# Configuration - reads from environment or defaults
# Load centralized configuration
try:
    config = get_config()
except Exception as e:
    # Logger might not be configured yet, but we will configure it shortly
    # or we can print to stderr
    print(f"CRITICAL: Configuration load failed: {e}")
    exit(1)

RECORDINGS_DIR = config.recordings_dir
PROCESSED_DIR = config.processed_dir
DB_PATH = config.db_path
CONFIG_DIR = config.config_dir

from core.logging_setup import setup_logging
from core.observability import init_observability, get_tracer, VIDEOS_PROCESSED, PROCESSING_DURATION, MODEL_INFERENCE_TIME

# Initialize structured logging
logger = setup_logging()

# Initialize Observability (Tracing, Sentry, Metrics)
init_observability("ml-worker")

def load_ml_models() -> dict:
    """Initialize ML models using ModelRegistry."""
    from core.registry.model_registry import ModelRegistry
    from ml_worker.models import HeatmapModel, ObjectTrackingModel, PersonDetectionModel
    
    registry = ModelRegistry()
    
    # Register available model classes
    registry.register_class('heatmap', HeatmapModel)
    registry.register_class('tracking', ObjectTrackingModel)
    registry.register_class('person_detection', PersonDetectionModel)
    
    return registry

def process_video(video_path: Path) -> dict:
    """
    Process a video file and extract analytics.
    
    This is a MOCK implementation. Replace with your actual ML model:
    - YOLOv8 for object detection
    - OpenCV for motion/heatmap analysis
    - TensorFlow/PyTorch for custom models
    
    Args:
        video_path: Path to the MP4 file
        
    Returns:
        dict with analytics results
    """
    logger.info(f"Processing: {video_path.name}")
    
    # =========================================
    # MOCK ML PROCESSING
    # Replace this with your actual ML code
    # =========================================
    import random
    
    # Simulate processing time
    time.sleep(2)
    
    # Generate mock results
    results = {
        "visitor_count": random.randint(0, 10),
        "motion_detected": random.choice([True, False]),
        "confidence": round(random.uniform(0.7, 0.99), 2)
    }
    
    logger.info(f"Results: {results}")
    return results



def scan_existing_files(handler: VideoHandler):
    """Process any existing files that haven't been processed yet."""
    if not RECORDINGS_DIR.exists():
        return
    
    tenant_id = os.environ.get("TENANT_ID", "default")
    for mp4_file in RECORDINGS_DIR.rglob("*.mp4"):
        if not handler.repo.is_processed(mp4_file.name, tenant_id=tenant_id):
            try:
                handler.process_file(mp4_file, tenant_id=tenant_id)
            except Exception as e:
                logger.error(f"Error processing existing file {mp4_file.name}: {e}")


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("  ML Video Consumer Started")
    logger.info("=" * 50)
    logger.info(f"Watching: {RECORDINGS_DIR}")
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Config:   {CONFIG_DIR}")
    
    # Initialize repository
    repo = get_repository()
    repo.init_schema()
    
    # Initialize Model Registry
    from core.registry.model_registry import ModelRegistry
    registry = ModelRegistry()
    registry.load_from_config(CONFIG_DIR / "models.yml")
    
    # Initialize Processing Service
    processing_service = ProcessingService(
        registry=registry,
        analytics_repo=repo,
        heatmap_repo=repo,
        tracking_repo=repo,
        person_detection_repo=repo
    )
    
    # Create directories
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Validated shutdown handling
    stop_event = threading.Event()

    # Set up file watcher
    handler = VideoHandler(processing_service, repo, stop_event=stop_event)
    observer = Observer()
    observer.schedule(handler, str(RECORDINGS_DIR), recursive=True)
    
    # Process existing files first
    logger.info("Scanning for existing files...")
    scan_existing_files(handler)
    
    # Start watching for new files
    observer.start()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        stop_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info(f"Watching for new recordings in {RECORDINGS_DIR}... (Press Ctrl+C to stop)")
    
    # Wait for stop signal
    try:
        while not stop_event.is_set():
            stop_event.wait(1.0)
    finally:
        logger.info("Stopping observer and waiting for in-progress tasks...")
        observer.stop()
        observer.join(timeout=30)
        
        # Explicit connection cleanup if needed (though get_connection is a context manager)
        # We can ping the DB to ensure it's still healthy or just log finalization
        logger.info("Graceful shutdown complete.")


if __name__ == "__main__":
    main()

