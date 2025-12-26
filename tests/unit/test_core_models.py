"""
Test Core Models (Phase A1)
===========================
Test result dataclasses: creation, serialization, defaults.
These have ZERO dependencies - test first!
"""

import pytest
import json
from datetime import datetime


class TestBaseResult:
    """Test BaseResult dataclass."""
    
    def test_create_with_required_fields(self):
        """Can create with just required fields."""
        from core.models.results import BaseResult
        
        result = BaseResult(
            camera_id="cam1",
            filename="video.mp4"
        )
        
        assert result.camera_id == "cam1"
        assert result.filename == "video.mp4"
    
    def test_default_values(self):
        """Default values are set correctly."""
        from core.models.results import BaseResult
        
        result = BaseResult(
            camera_id="cam1",
            filename="video.mp4"
        )
        
        assert result.camera_name == ""
        assert result.camera_location == ""
        assert isinstance(result.timestamp, datetime)
    
    def test_to_dict(self):
        """to_dict() converts to dictionary with ISO timestamp."""
        from core.models.results import BaseResult
        
        result = BaseResult(
            camera_id="cam1",
            filename="video.mp4",
            camera_name="Test Camera"
        )
        
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert data["camera_id"] == "cam1"
        assert data["camera_name"] == "Test Camera"
        assert isinstance(data["timestamp"], str)  # Should be ISO string
    
    def test_get_result_type(self):
        """get_result_type returns 'base'."""
        from core.models.results import BaseResult
        
        assert BaseResult.get_result_type() == "base"


class TestAnalyticsResult:
    """Test AnalyticsResult dataclass."""
    
    def test_create_with_all_fields(self):
        """Can create with all fields."""
        from core.models.results import AnalyticsResult
        
        result = AnalyticsResult(
            camera_id="cam1",
            filename="video.mp4",
            visitor_count=10,
            motion_detected=True,
            confidence=0.95
        )
        
        assert result.visitor_count == 10
        assert result.motion_detected is True
        assert result.confidence == 0.95
    
    def test_default_values(self):
        """Analytics-specific defaults are correct."""
        from core.models.results import AnalyticsResult
        
        result = AnalyticsResult(
            camera_id="cam1",
            filename="video.mp4"
        )
        
        assert result.visitor_count == 0
        assert result.motion_detected is False
        assert result.confidence == 0.0
    
    def test_get_result_type(self):
        """get_result_type returns 'analytics'."""
        from core.models.results import AnalyticsResult
        
        assert AnalyticsResult.get_result_type() == "analytics"


class TestHeatmapResult:
    """Test HeatmapResult dataclass."""
    
    def test_create_with_all_fields(self):
        """Can create with heatmap-specific fields."""
        from core.models.results import HeatmapResult
        
        result = HeatmapResult(
            camera_id="cam1",
            filename="video.mp4",
            heatmap_path="/path/to/heatmap.png",
            hotspot_count=5,
            max_density=0.8,
            avg_motion=0.3
        )
        
        assert result.heatmap_path == "/path/to/heatmap.png"
        assert result.hotspot_count == 5
        assert result.max_density == 0.8
    
    def test_grid_data_parsing(self):
        """get_grid_data() parses JSON string."""
        from core.models.results import HeatmapResult
        
        grid = {"cells": [[1, 2], [3, 4]], "size": [2, 2]}
        result = HeatmapResult(
            camera_id="cam1",
            filename="video.mp4",
            grid_data=json.dumps(grid)
        )
        
        parsed = result.get_grid_data()
        assert parsed["cells"] == [[1, 2], [3, 4]]
        assert parsed["size"] == [2, 2]
    
    def test_invalid_grid_data(self):
        """get_grid_data() returns empty dict for invalid JSON."""
        from core.models.results import HeatmapResult
        
        result = HeatmapResult(
            camera_id="cam1",
            filename="video.mp4",
            grid_data="not valid json"
        )
        
        parsed = result.get_grid_data()
        assert parsed == {}
    
    def test_get_result_type(self):
        """get_result_type returns 'heatmap'."""
        from core.models.results import HeatmapResult
        
        assert HeatmapResult.get_result_type() == "heatmap"


class TestTrackingResult:
    """Test TrackingResult dataclass."""
    
    def test_create_with_all_fields(self):
        """Can create with tracking-specific fields."""
        from core.models.results import TrackingResult
        
        result = TrackingResult(
            camera_id="cam1",
            filename="video.mp4",
            object_count=15,
            entries=8,
            exits=7,
            avg_speed=5.5
        )
        
        assert result.object_count == 15
        assert result.entries == 8
        assert result.exits == 7
        assert result.avg_speed == 5.5
    
    def test_trajectories_parsing(self):
        """get_trajectories() parses JSON string."""
        from core.models.results import TrackingResult
        
        trajectories = [
            {"id": 1, "path": [[0, 0], [10, 10]]},
            {"id": 2, "path": [[5, 5], [15, 15]]}
        ]
        result = TrackingResult(
            camera_id="cam1",
            filename="video.mp4",
            trajectories=json.dumps(trajectories)
        )
        
        parsed = result.get_trajectories()
        assert len(parsed) == 2
        assert parsed[0]["id"] == 1
    
    def test_get_result_type(self):
        """get_result_type returns 'tracking'."""
        from core.models.results import TrackingResult
        
        assert TrackingResult.get_result_type() == "tracking"


class TestPersonDetectionResult:
    """Test PersonDetectionResult dataclass."""
    
    def test_create_with_all_fields(self):
        """Can create with detection-specific fields."""
        from core.models.results import PersonDetectionResult
        
        result = PersonDetectionResult(
            camera_id="cam1",
            filename="video.mp4",
            total_detections=100,
            max_people=10,
            avg_people=4.5
        )
        
        assert result.total_detections == 100
        assert result.max_people == 10
        assert result.avg_people == 4.5
    
    def test_detections_parsing(self):
        """get_detections() parses JSON string."""
        from core.models.results import PersonDetectionResult
        
        detections = [
            {"frame": 0, "humans": [{"x": 100, "y": 200}]},
            {"frame": 1, "humans": [{"x": 110, "y": 210}]}
        ]
        result = PersonDetectionResult(
            camera_id="cam1",
            filename="video.mp4",
            detections_json=json.dumps(detections)
        )
        
        parsed = result.get_detections()
        assert len(parsed) == 2
        assert parsed[0]["frame"] == 0
    
    def test_get_result_type(self):
        """get_result_type returns 'person_detection'."""
        from core.models.results import PersonDetectionResult
        
        assert PersonDetectionResult.get_result_type() == "person_detection"


class TestResultTypeRegistry:
    """Test the RESULT_TYPES registry."""
    
    def test_get_result_class_analytics(self):
        """Can get AnalyticsResult class by type string."""
        from core.models.results import get_result_class, AnalyticsResult
        
        cls = get_result_class("analytics")
        assert cls == AnalyticsResult
    
    def test_get_result_class_heatmap(self):
        """Can get HeatmapResult class by type string."""
        from core.models.results import get_result_class, HeatmapResult
        
        cls = get_result_class("heatmap")
        assert cls == HeatmapResult
    
    def test_get_result_class_unknown(self):
        """Unknown type returns BaseResult."""
        from core.models.results import get_result_class, BaseResult
        
        cls = get_result_class("unknown_type")
        assert cls == BaseResult
