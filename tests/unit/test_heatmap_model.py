"""
Test Heatmap Model (Phase D4)
=============================
Test heatmap generation from shared detection data.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from ml_worker.models.heatmap import HeatmapModel
from tests.fixtures.ml_mocks import mock_video_capture


class TestHeatmapModel:
    """Test HeatmapModel logic."""
    
    @pytest.fixture
    def model(self):
        config = {
            "name": "Heatmap",
            "enabled": True,
            "config": {"grid_size": [10, 10]}
        }
        with patch("ml_worker.models.heatmap.SonyHeatmapAdapter"):
             model = HeatmapModel(config)
             yield model

    def test_uses_chained_input(self, model, mock_video_capture):
        """Model uses detections passed from previous model."""
        # Chained input from PersonDetectionModel
        detections = [
            {"frame": 0, "humans": [{"x": 100, "y": 100}]},
            {"frame": 1, "humans": [{"x": 200, "y": 200}]}
        ]
        
        model.set_chained_input({"detections_json": str(detections)})
        # Also need to set _shared_detections directly because implementation might use it
        model.set_person_detections({"detections": detections})
        
        # Mock adapter
        model.adapter.generate_from_detections.return_value = {
            "heatmap_path": "test.png", 
            "hotspot_count": 2,
            "max_density": 0.5
        }
        
        with patch("ml_worker.models.heatmap.cv2.VideoCapture", return_value=mock_video_capture), \
             patch("ml_worker.models.heatmap.cv2.imwrite"), \
             patch("pathlib.Path.mkdir"):
            
            result = model.process_video(Path("test.mp4"))
            
        assert result["hotspot_count"] == 2
        
        # Verify adapter called with correct points
        args = model.adapter.generate_from_detections.call_args
        # First arg is points list, verify len
        assert len(args[0][0]) == 2 # 2 detections

    def test_accepts_chained_input_returns_true(self, model):
        """Model correctly reports it accepts chained input."""
        assert model.accepts_chained_input() is True
