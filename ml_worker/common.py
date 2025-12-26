import os
import time
import logging
import threading
import shutil
import json
from pathlib import Path
from datetime import datetime
from watchdog.events import FileSystemEventHandler

from services.processing_service import ProcessingService, CameraInfo
from core.observability import get_tracer, VIDEOS_PROCESSED, PROCESSING_DURATION
from ml_worker.config_loader import load_camera_config

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Camera configuration cache
_camera_config = None

def get_camera_info(camera_id: str, config_dir: Path) -> CameraInfo:
    """Helper to get camera metadata."""
    configs = load_camera_config(config_dir)
    for cam in configs.get("cameras", []):
        if cam["id"] == camera_id:
            return CameraInfo(**cam)
    return CameraInfo(id=camera_id, name=camera_id)

class VideoHandler(FileSystemEventHandler):
    """Handles new video file events."""
    
    def __init__(self, processing_service: ProcessingService, repo, stop_event: threading.Event = None, config_dir: Path = None):
        self.processing_service = processing_service
        self.repo = repo
        self.stop_event = stop_event or threading.Event()
        self.config_dir = config_dir
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        tenant_id = os.environ.get("TENANT_ID", "default")
        
        # Only process MP4 files
        if file_path.suffix.lower() != ".mp4":
            return
        
        # Skip if already processed (atomic check)
        if self.repo.is_processed(file_path.name, tenant_id=tenant_id):
            return
        
        # Wait for file to be fully written
        time.sleep(2)
        
        # CRITICAL STABILITY CHECK: Queue TTL
        file_age = time.time() - file_path.stat().st_mtime
        ttl_seconds = int(os.environ.get("QUEUE_TTL_SECONDS", 300))
        
        if file_age > ttl_seconds:
            logger.error(f"🚨 DATA LOSS: Skipping {file_path.name} (Age: {int(file_age)}s > TTL {ttl_seconds}s)")
            
            # Move to quarantine instead of deleting
            SKIPPED_DIR = Path(os.environ.get("SKIPPED_DIR", "/app/data/skipped"))
            SKIPPED_DIR.mkdir(parents=True, exist_ok=True)
            skipped_path = SKIPPED_DIR / file_path.name
            
            try:
                shutil.move(str(file_path), str(skipped_path))
                
                # Store metadata for audit
                metadata = {
                    'original_path': str(file_path),
                    'age_seconds': file_age,
                    'ttl_seconds': ttl_seconds,
                    'timestamp': datetime.now().isoformat()
                }
                (SKIPPED_DIR / f"{file_path.stem}.metadata.json").write_text(json.dumps(metadata))
            except Exception as e:
                logger.error(f"Failed to move skipped file: {e}")
            
            return

        try:
            self.process_file(file_path, tenant_id=tenant_id)
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            VIDEOS_PROCESSED.labels(camera_id='unknown', status='error', model='pipeline').inc()
    
    @PROCESSING_DURATION.labels(model='pipeline').time()
    def process_file(self, file_path: Path, tenant_id: str = "default"):
        """Process a single video file with all enabled models (with chaining)."""
        with tracer.start_as_current_span("process_file") as span:
            span.set_attribute("filename", file_path.name)
            span.set_attribute("tenant_id", tenant_id)

            # Extract camera ID from path or filename
            parts = file_path.parts
            camera_id = "cam_default"
            
            # Try to find camera ID in path (recordings/<camera_id>/...)
            for i, part in enumerate(parts):
                if part == "recordings" and i + 1 < len(parts):
                    camera_id = parts[i + 1]
                    break
            
            # Get camera metadata from config
            camera_info = get_camera_info(camera_id, self.config_dir)
            
            logger.info(f"Processing {file_path.name} from camera {camera_info.name} (Tenant: {tenant_id})")
            
            # Atomic check-and-set
            if not self.repo.mark_processed(file_path.name, camera_id=camera_id, tenant_id=tenant_id):
                logger.info(f"File {file_path.name} already being processed by another worker for tenant {tenant_id}")
                return

            try:
                # Process via service layer
                result = self.processing_service.process_video(
                    video_path=file_path,
                    camera_info=camera_info,
                    tenant_id=tenant_id
                )
                
                if result.success:
                    logger.info(f"Successfully processed {file_path.name}")
                    VIDEOS_PROCESSED.labels(camera_id=camera_id, status='success', model='pipeline').inc()
                else:
                    logger.error(f"Processing failed for {file_path.name}: {result.errors}")
                    VIDEOS_PROCESSED.labels(camera_id=camera_id, status='error', model='pipeline').inc()
                    
            except Exception as e:
                logger.error(f"Error in process_file for {file_path.name}: {e}")
                VIDEOS_PROCESSED.labels(camera_id=camera_id, status='error', model='pipeline').inc()
                raise

            logger.info("video_processed", filename=file_path.name, status="success")
