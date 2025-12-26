"""
Test Tracking Model (Phase D3)
==============================
Test object tracking logic: line crossing, entry/exit counting.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ml_worker.models.tracking import ObjectTrackingModel
from tests.fixtures.ml_mocks import mock_video_capture


class TestTrackingModel:
    """Test ObjectTrackingModel logic."""
    
    @pytest.fixture
    def model(self):
        config = {
            "name": "Tracking",
            "enabled": True,
            "config": {
                "model_size": "yolov8n.pt",
                "line_position": 0.5,
                "line_orientation": "horizontal"
            }
        }
        with patch("ml_worker.models.tracking.YOLO"):
            model = ObjectTrackingModel(config)
            yield model

    def test_line_crossing_counting(self, model, mock_video_capture):
        """Test entry/exit counting based on line crossing."""
        # Setup mock tracks: object 1 moves from y=0.1 to y=0.9 (crosses 0.5 down)
        # Mock result structure for YOLO track
        track_res = MagicMock()
        # Boxes has id property which returns IDs
        track_res.boxes.id.tolist.return_value = [1]
        # Boxes has xywhn for position
        # Frame 1: y=0.1
        track_res.boxes.xywhn.tolist.return_value = [[0.5, 0.1, 0.1, 0.1]]
        
        track_res2 = MagicMock()
        track_res2.boxes.id.tolist.return_value = [1]
        # Frame 2: y=0.9
        track_res2.boxes.xywhn.tolist.return_value = [[0.5, 0.9, 0.1, 0.1]]
        
        model.model = MagicMock()
        # Return frame 1 then frame 2 then empty/none for rest
        model.model.track.side_effect = [[track_res], [track_res2]] + [[]] * 28
        
        with patch("ml_worker.models.tracking.cv2.VideoCapture", return_value=mock_video_capture):
            result = model.process_video(Path("test.mp4"))
            
        # Should detect 1 object
        assert result["object_count"] == 1
        
        # Depending on orientation/direction logic:
        # 0.1 -> 0.9 is moving "down" (often counted as entry or exit depending on definition)
        # Assuming code counts crossing:
        assert (result["entries"] + result["exits"]) >= 1

    def test_empty_video_handling(self, model, mock_video_capture):
        """Model handles video with no objects."""
        model.model = MagicMock()
        model.model.track.return_value = []
        
        with patch("ml_worker.models.tracking.cv2.VideoCapture", return_value=mock_video_capture):
            result = model.process_video(Path("test.mp4"))
            
        assert result["object_count"] == 0
        assert result["entries"] == 0
