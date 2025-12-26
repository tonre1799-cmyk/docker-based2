"""
Object Tracking Model (Enhanced)
================================
Tracks people across video frames using YOLOv8 + ByteTrack.
Counts unique entries/exits across a defined line.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import json
import sys
from ultralytics import YOLO
import sys

# Add parent directory to path to import base modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.base_model import BaseMLModel


class ObjectTrackingModel(BaseMLModel):
    """
    Person tracking and counting model using YOLOv8.
    """
    
    def __init__(self, config: dict):
        super().__init__("tracking", config)
        
        # Load YOLOv8 model for tracking
        # We use a purely detection-based model here, but Ultralytics supports
        # tracking out-of-the-box with .track() method
        model_size = self.config.get('model_size', 'yolov8n.pt')
        
        # Check pinned weights first
        weights_dir = Path("/app/models/weights")
        if (weights_dir / model_size).exists():
           self.model = YOLO(str(weights_dir / model_size))
        else:
           self.model = YOLO(model_size)
        
        # Tracking configuration
        self.conf_threshold = self.config.get('confidence', 0.5)
        self.iou_threshold = self.config.get('iou', 0.5)
        self.tracker_type = self.config.get('tracker', 'bytetrack.yaml') # or botsort.yaml
        
        # Line counting configuration
        # Default line is horizontal at 50% height
        self.line_position = self.config.get('line_position', 0.5) 
        self.line_orientation = self.config.get('line_orientation', 'horizontal')
        
        # Stability / Performance Configuration
        # Process every Nth frame (e.g., 3 means 30fps -> 10fps processing)
        self.frame_skip = self.config.get('frame_skip', 3)
        # Downscale large videos to this width for faster inference
        self.max_width = self.config.get('resize_width', 640)
    
    def get_result_type(self) -> str:
        """Return result type for repository selection."""
        return 'tracking'
        
    def process_video(self, video_path: Path, context=None) -> Dict[str, Any]:
        """
        Track people and count line crossings in a video chunk.
        
        Args:
            video_path: Path to MP4 video file
            config_overrides: Optional dict to override instance config (e.g., per-camera line settings)
            
        Returns:
            Dictionary with tracking analytics (counts, trajectories, metadata)
        """
        # Determine configuration to use (instance default vs override from context)
        active_config = self.config.copy()
        config_overrides = context.config_overrides if context and hasattr(context, 'config_overrides') else {}
        if config_overrides:
            active_config.update(config_overrides)
            
        line_pos = active_config.get('line_position', self.line_position)
        line_ori = active_config.get('line_orientation', self.line_orientation)
        
        # Open video to get dimensions
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return self._empty_result()
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        # Define counting line
        if line_ori == 'horizontal':
            line_y = int(height * line_pos)
            line_p1 = (0, line_y)
            line_p2 = (width, line_y)
        else: # vertical
            line_x = int(width * line_pos)
            line_p1 = (line_x, 0)
            line_p2 = (line_x, height)
            
        # Run YOLOv8 Tracking
        # persist=True is crucial for tracking across frames
        results = self.model.track(
            source=str(video_path),
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=[0], # 0 = person
            tracker=self.tracker_type,
            persist=True,
            verbose=False,
            stream=True,
            vid_stride=self.frame_skip  # Native YOLO frame skipping
        )
        
        # Analytics storage
        tracks = {} # ID -> {positions: [], crossed: False}
        entries = 0
        exits = 0
        unique_ids = set()
        
        # Collection for HeatmapModel (frame-by-frame detections)
        all_detections = []
        
        # Note: When skipping frames, frame_idx will jump (0, 3, 6...)
        # We need to map this correctly if Heatmap expects continuous frames,
        # but usually it just plots points so it's fine.
        frame_idx = 0 
        for r in results:
            # Adjust frame index based on stride
            # current_frame = frame_idx * self.frame_skip
            
            frame_detections = []
            frame_detections = []
            
            if r.boxes is not None and r.boxes.id is not None:
                # Get boxes and track IDs
                boxes = r.boxes.xywh.cpu().numpy()
                track_ids = r.boxes.id.int().cpu().tolist()
                
                for box, track_id in zip(boxes, track_ids):
                    x, y, w, h = box
                    center_x, center_y = int(x), int(y)
                    
                    # Store for heatmap
                    frame_detections.append({
                        'x': center_x,
                        'y': center_y,
                        'track_id': track_id
                    })
                    
                    unique_ids.add(track_id)
                    
                    # Initialize track if simple
                    if track_id not in tracks:
                        tracks[track_id] = {
                            'positions': [],
                            'crossed': False,
                            'direction': 0 # 1=entry, -1=exit
                        }
                    
                    # Add position
                    current_pos = (center_x, center_y)
                    previous_pos = tracks[track_id]['positions'][-1] if tracks[track_id]['positions'] else None
                    tracks[track_id]['positions'].append(current_pos)
                    
                    # Check line crossing if we have previous position
                    if previous_pos and not tracks[track_id]['crossed']:
                        prev_x, prev_y = previous_pos
                        curr_x, curr_y = current_pos
                        
                        crossed = False
                        direction = 0
                        
                        if line_ori == 'horizontal':
                            # Check if crossed horizontal line Y
                            if (prev_y < line_y and curr_y >= line_y): # Moving Down (Entry)
                                crossed = True
                                direction = 1
                            elif (prev_y > line_y and curr_y <= line_y): # Moving Up (Exit)
                                crossed = True
                                direction = -1
                        else:
                            # Check if crossed vertical line X
                            if (prev_x < line_x and curr_x >= line_x): # Moving Right (Entry)
                                crossed = True
                                direction = 1
                            elif (prev_x > line_x and curr_x <= line_x): # Moving Left (Exit)
                                crossed = True
                                direction = -1
                                
                        if crossed:
                            tracks[track_id]['crossed'] = True
                            tracks[track_id]['direction'] = direction
                            if direction == 1:
                                entries += 1
                            else:
                                exits += 1

            # Append frame data
            all_detections.append({
                'frame': frame_idx,
                'humans': frame_detections
            })
            frame_idx += 1
            
        # Format trajectories for storage (simplify data reduction)
        serialized_tracks = []
        for tid, data in tracks.items():
            # Only save tracks that moved enough or crossed
            if len(data['positions']) > 5:
                serialized_tracks.append({
                    'id': tid,
                    'path': data['positions'][::5], # Subsample for size
                    'crossed': data['crossed'],
                    'direction': data['direction']
                })
        
        return {
            'object_count': len(unique_ids),
            'unique_visitors': len(unique_ids),
            'entries': entries,
            'exits': exits,
            'trajectories': json.dumps(serialized_tracks),
            'detections': all_detections, # Shared with HeatmapModel
            'avg_speed': 0.0, # Placeholder
            'max_objects': 0, # Placeholder
            'metadata': {
                'width': width,
                'height': height,
                'total_frames': total_frames,
                'line_orientation': self.line_orientation,
                'line_position': self.line_position
            }
        }

    def _empty_result(self):
        return {
            'object_count': 0,
            'unique_visitors': 0,
            'entries': 0,
            'exits': 0,
            'trajectories': '[]',
            'avg_speed': 0.0,
            'max_objects': 0
        }
