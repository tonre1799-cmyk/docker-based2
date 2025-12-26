"""
Person Detection Model
======================
YOLOv8-based person detection for retail analytics.
Detects person positions (x, y coordinates) for heatmap generation.
"""

import cv2
import json
from pathlib import Path
from typing import Dict, Any
from ultralytics import YOLO
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base_model import BaseMLModel


class PersonDetectionModel(BaseMLModel):
    """YOLOv8-based person detection model."""
    
    def __init__(self, config: dict):
        super().__init__("person_detection", config)
        model_size = self.config.get('model_size', 'yolov8n.pt')
        
        # Check pinned weights first
        weights_dir = Path("/app/models/weights")
        if (weights_dir / model_size).exists():
            self.model = YOLO(str(weights_dir / model_size))
        else:
            self.model = YOLO(model_size)
        self.confidence_threshold = self.config.get('confidence', 0.5)
        self.detect_every_n_frames = self.config.get('frame_skip', 1)  # Process every frame by default
    
    def get_result_type(self) -> str:
        """Return result type for repository selection."""
        return 'person_detection'
    
    def process_video(self, video_path: Path, context=None) -> Dict[str, Any]:
        """
        Detect people in video and return frame-by-frame positions.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Person detection statistics and frame-by-frame data
        """
        detections_per_frame = []
        
        # Run YOLO inference
        results = self.model(
            str(video_path),
            stream=True,
            classes=[0],  # Person class only
            conf=self.confidence_threshold,
            verbose=False
        )
        
        frame_idx = 0
        for r in results:
            # Skip frames if configured
            if frame_idx % self.detect_every_n_frames != 0:
                frame_idx += 1
                continue
            
            frame_detections = []
            
            # Extract person bounding boxes
            if r.boxes is not None and len(r.boxes) > 0:
                for box in r.boxes:
                    # Get center coordinates
                    xyxy = box.xyxy[0].cpu().numpy()
                    x_center = int((xyxy[0] + xyxy[2]) / 2)
                    y_center = int((xyxy[1] + xyxy[3]) / 2)
                    confidence = float(box.conf[0])
                    
                    frame_detections.append({
                        'x': x_center,
                        'y': y_center,
                        'confidence': confidence,
                        'bbox': xyxy.tolist()
                    })
            
            detections_per_frame.append({
                'frame': frame_idx,
                'humans': frame_detections
            })
            
            frame_idx += 1
        
        # Calculate statistics
        if not detections_per_frame:
            return {
                'total_detections': 0,
                'max_people': 0,
                'avg_people': 0.0,
                'detections': []
            }
        
        people_per_frame = [len(f['humans']) for f in detections_per_frame]
        
        return {
            'total_detections': sum(people_per_frame),
            'max_people': max(people_per_frame) if people_per_frame else 0,
            'avg_people': sum(people_per_frame) / len(people_per_frame) if people_per_frame else 0.0,
            'detections': detections_per_frame  # For Sony heatmap
        }
