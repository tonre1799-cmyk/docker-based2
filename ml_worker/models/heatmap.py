"""
Heatmap Model
=============
Generates human-specific motion heatmap using Sony AITRIOS adapter.
Requires person detection data from PersonDetectionModel.
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, Any
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base_model import BaseMLModel
from models.grid_heatmap_generator import GridBasedHeatmapGenerator


class HeatmapModel(BaseMLModel):
    """Human-specific heatmap generation using Grid approach."""
    
    def __init__(self, config: dict):
        super().__init__("heatmap", config)
        grid_size = tuple(self.config.get('grid_size', [10, 10]))
        self.adapter = GridBasedHeatmapGenerator(grid_size=grid_size)
    
    def get_result_type(self) -> str:
        """Return result type for repository selection."""
        return 'heatmap'
    
    def accepts_chained_input(self) -> bool:
        """Heatmap can use person detection data."""
        return True
    
    def set_person_detections(self, detections_result: dict):
        """Receive detections from PersonDetectionModel or TrackingModel."""
        self._shared_detections = detections_result.get('detections', [])
    
    def process_video(self, video_path: Path, context=None) -> Dict[str, Any]:
        """
        Generate heatmap from video. 
        Uses set_person_detections() data if available, otherwise runs internal detection.
        """
        # If we have external Yolo detections (from PersonDetectionModel or ObjectTrackingModel)
        # transform them into heatmap points
        if self._shared_detections:
            return self._process_from_detections(video_path, self._shared_detections)
            
        # Fallback: legacy background subtraction or internal detection
        return self._generate_basic_heatmap(video_path)

    def _process_from_detections(self, video_path: Path, detections: list) -> Dict[str, Any]:
        """Generate heatmap using Yolo detection centers."""
        heatmap_points = []
        
        for frame_data in detections:
            # Handle both format types (PersonDetectionModel vs TrackingModel output)
            # TrackingModel might output trajectories, PersonDetection outputs frame-by-frame
            
            # If standard PersonDetectionModel format
            if 'humans' in frame_data:
                for person in frame_data['humans']:
                    heatmap_points.append({
                        'x': person['x'],
                        'y': person['y'],
                        'value': 1 # simple count
                    })
                    
        # If no points, return callback if no detections
        if not heatmap_points:
             return self._generate_basic_heatmap(video_path)
             
        # Generate heatmap using Sony adapter
        # We need video dimensions
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
             return self._generate_basic_heatmap(video_path)
             
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        ret, background_frame = cap.read()
        cap.release()

        # Generate heatmap using adapter
        # Need to reformat simple points to adapter expected format if needed
        # Adapter expects: 'detections': [{'x': 100, 'y': 200}, ...]
        adapter_input = [{'x': p['x'], 'y': p['y']} for p in heatmap_points]
        
        result = self.adapter.generate_from_detections(
            adapter_input,
            frame_width,
            frame_height,
            background_frame if ret else None
        )
        
        # Save heatmap image
        heatmap_dir = video_path.parent / "heatmaps"
        heatmap_dir.mkdir(parents=True, exist_ok=True)
        heatmap_path = heatmap_dir / f"{video_path.stem}_heatmap.png"
        cv2.imwrite(str(heatmap_path), result['heatmap_image'])
        
        return {
            'heatmap_path': str(heatmap_path),
            'hotspot_count': result['hotspot_count'],
            'max_density': result['max_density'],
            'avg_motion': result['avg_density'],
            'grid_data': json.dumps(result['grid_data'])
        }
    
    def _generate_basic_heatmap(self, video_path: Path) -> Dict[str, Any]:
        """
        Fallback: basic motion heatmap when no person detection available.
        Uses frame differencing (original implementation).
        """
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {
                'heatmap_path': '',
                'hotspot_count': 0,
                'max_density': 0.0,
                'avg_motion': 0.0,
                'grid_data': '{}'
            }
        
        heatmap = None
        prev_gray = None
        frame_count = 0
        total_motion = 0
        threshold = 25
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)
            
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
                
                if heatmap is None:
                    heatmap = thresh.astype(np.float32)
                else:
                    heatmap += thresh.astype(np.float32)
                
                total_motion += np.sum(thresh) / 255.0
            
            prev_gray = gray
            frame_count += 1
        
        cap.release()
        
        if heatmap is None:
            return {
                'heatmap_path': '',
                'hotspot_count': 0,
                'max_density': 0.0,
                'avg_motion': 0.0,
                'grid_data': '{}'
            }
        
        # Normalize and colorize
        heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
        
        # Save
        heatmap_dir = video_path.parent / "heatmaps"
        heatmap_dir.mkdir(exist_ok=True)
        heatmap_path = heatmap_dir / f"{video_path.stem}_heatmap_basic.png"
        cv2.imwrite(str(heatmap_path), heatmap_color)
        
        hotspot_threshold = 0.7 * 255
        hotspots = int(np.sum(heatmap_norm > hotspot_threshold))
        
        return {
            'heatmap_path': str(heatmap_path),
            'hotspot_count': len(hotspots),
            'max_density': float(np.max(heatmap_norm)),
            'avg_motion': float(np.mean(heatmap_norm))
        }
