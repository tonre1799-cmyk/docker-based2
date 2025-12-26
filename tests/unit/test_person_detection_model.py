"""
Test Person Detection Model (Phase D2)
======================================
Test YOLO detection logic with mocked model and video.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json

from ml_worker.models.person_detection import PersonDetectionModel
from tests.fixtures.ml_mocks import mock_video_capture, mock_yolo_model


class TestPersonDetectionModel:
    """Test PersonDetectionModel logic."""
    
    @pytest.fixture
    def model(self):
        config = {
            "name": "Person Detection",
            "enabled": True,
            "config": {
                "model_size": "yolov8n.pt",
                "confidence": 0.5,
                "frame_skip": 1,
                "camera_id": "cam1"
            }
        }
        # Patch YOLO load
        with patch("ml_worker.models.person_detection.YOLO"):
            model = PersonDetectionModel(config)
            yield model
            
    def test_initialization(self, model):
        """Model initializes correctly."""
        assert model.name == "Person Detection"
        assert model.confidence == 0.5
        assert model.get_result_type() == "person_detection"
    
    def test_process_video_detects_people(self, model, mock_video_capture, mock_yolo_model):
        """Process video finds people and returns stats."""
        # Setup mocks
        model.model = mock_yolo_model
        
        # Call process_video
        with patch("ml_worker.models.person_detection.cv2.VideoCapture", return_value=mock_video_capture):
            result = model.process_video(Path("test.mp4"))
            
        assert result["total_detections"] == 30 # 30 frames * 1 detection/frame
        assert result["max_people"] == 1
        assert "detections_json" in result
        
        # Verify JSON structure
        detections = json.loads(result["detections_json"])
        assert len(detections) > 0
        assert "humans" in detections[0]
        
    def test_frame_skip_logic(self, model, mock_video_capture):
        """Model skips frames according to config."""
        model.config["config"]["frame_skip"] = 2
        model.frame_skip = 2
        
        # Mock model to track calls
        model.model = MagicMock()
        model.model.return_value = [] # No detections for simplicity
        
        with patch("ml_worker.models.person_detection.cv2.VideoCapture", return_value=mock_video_capture):
            model.process_video(Path("test.mp4"))
            
        # 30 frames total, skip 2 = process every 2nd frame = 15 calls
        assert model.model.call_count == 15
