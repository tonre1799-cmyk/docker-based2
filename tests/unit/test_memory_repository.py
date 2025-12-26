"""
Test Memory Repository (Phase B1)
=================================
Verify that the in-memory repository correctly implements the interface.
This ensures our service tests will be valid.
"""

import pytest
from tests.fixtures.mock_factories import (
    MockAnalyticsRepository,
    MockHeatmapRepository,
    MockTrackingRepository,
    MockPersonDetectionRepository
)


class TestMockAnalyticsRepository:
    """Test MockAnalyticsRepository functionality."""
    
    def test_save_and_get_results(self):
        """Can save and retrieve analytics results."""
        repo = MockAnalyticsRepository()
        
        # Save 3 results
        repo.save_result("cam1", "video1.mp4", 5, True, 0.9)
        repo.save_result("cam1", "video2.mp4", 3, False, 0.8)
        repo.save_result("cam2", "video3.mp4", 2, True, 0.7)
        
        # Get all results
        results = repo.get_results(limit=10)
        assert len(results) == 3
        # Should be reversed (LIFO)
        assert results[0]["camera_id"] == "cam2"
        
        # Filter by camera
        cam1_results = repo.get_results(camera_id="cam1")
        assert len(cam1_results) == 2
        assert all(r["camera_id"] == "cam1" for r in cam1_results)
    
    def test_get_stats(self):
        """Calculates correct statistics."""
        repo = MockAnalyticsRepository()
        
        repo.save_result("cam1", "v1", 10, True, 1.0)
        repo.save_result("cam1", "v2", 20, False, 0.5)
        
        stats = repo.get_stats(camera_id="cam1")
        
        assert stats["total_events"] == 2
        assert stats["total_visitors"] == 30
        assert stats["avg_confidence"] == 0.75
        assert stats["motion_events"] == 1


class TestMockHeatmapRepository:
    """Test MockHeatmapRepository functionality."""
    
    def test_save_and_get_heatmaps(self):
        """Can save and retrieve heatmaps."""
        repo = MockHeatmapRepository()
        
        repo.save_heatmap("cam1", "v1.mp4", "/path/1.png", 5, 0.8)
        repo.save_heatmap("cam1", "v2.mp4", "/path/2.png", 3, 0.6)
        
        results = repo.get_heatmaps(camera_id="cam1")
        assert len(results) == 2
        assert results[0]["hotspot_count"] == 3
    
    def test_get_heatmap_stats(self):
        """Calculates correct heatmap stats."""
        repo = MockHeatmapRepository()
        repo.save_heatmap("cam1", "v1", "p1", 10, 1.0, 0.5)
        repo.save_heatmap("cam1", "v2", "p2", 20, 0.5, 0.3)
        
        stats = repo.get_heatmap_stats("cam1")
        assert stats["total_heatmaps"] == 2
        assert stats["avg_hotspots"] == 15.0  # (10+20)/2
        assert stats["max_density"] == 1.0
        assert stats["avg_motion"] == 0.4


class TestMockTrackingRepository:
    """Test MockTrackingRepository functionality."""
    
    def test_save_and_get_tracking(self):
        """Can save and retrieve tracking events."""
        repo = MockTrackingRepository()
        
        repo.save_tracking_event("cam1", "v1", object_count=5, avg_speed=10.0)
        
        results = repo.get_tracking_events("cam1")
        assert len(results) == 1
        assert results[0]["object_count"] == 5
    
    def test_tracking_stats(self):
        """Calculates correct tracking stats."""
        repo = MockTrackingRepository()
        repo.save_tracking_event("cam1", "v1", object_count=2, max_objects=1)
        repo.save_tracking_event("cam1", "v2", object_count=4, max_objects=3)
        
        stats = repo.get_tracking_stats("cam1")
        assert stats["total_objects"] == 6
        assert stats["peak_objects"] == 3


class TestMockPersonDetectionRepository:
    """Test MockPersonDetectionRepository functionality."""
    
    def test_save_and_get_detections(self):
        """Can save and retrieve person detections."""
        repo = MockPersonDetectionRepository()
        
        repo.save_person_detection("cam1", "v1", total_detections=100)
        
        results = repo.get_person_detections("cam1")
        assert len(results) == 1
        assert results[0]["total_detections"] == 100
        
    def test_detection_stats(self):
        """Calculates correct detection stats."""
        repo = MockPersonDetectionRepository()
        repo.save_person_detection("cam1", "v1", max_people=5, avg_people=2.0)
        repo.save_person_detection("cam1", "v2", max_people=10, avg_people=4.0)
        
        stats = repo.get_person_detection_stats("cam1")
        assert stats["peak_occupancy"] == 10
        assert stats["avg_people"] == 3.0
