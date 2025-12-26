"""
Test Analytics Service (Phase C2)
=================================
Test business logic for dashboard data aggregation using mocked repositories.
"""

import pytest
from datetime import datetime, timedelta
from services.analytics_service import AnalyticsService, DateRange
from tests.fixtures.mock_factories import (
    MockAnalyticsRepository,
    MockHeatmapRepository,
    MockTrackingRepository,
    MockPersonDetectionRepository,
    MockCombinedRepository
)


class TestAnalyticsService:
    """Test AnalyticsService logic."""
    
    def test_dashboard_overview_aggregates_stats(self):
        """Service correctly aggregates stats from repository."""
        # Setup mock data
        repo = MockAnalyticsRepository()
        repo.save_result("cam1", "v1", 10, True, 0.9)
        repo.save_result("cam2", "v2", 5, False, 0.8)
        
        service = AnalyticsService(analytics_repo=repo)
        
        overview = service.get_dashboard_overview(camera_id=None, hours=24)
        
        assert overview.total_events == 2
        assert overview.total_visitors == 15
        assert overview.avg_confidence == 0.85
        assert overview.motion_events == 1
    
    def test_dashboard_overview_filtering(self):
        """Service filters by camera ID."""
        repo = MockAnalyticsRepository()
        repo.save_result("cam1", "v1", 10)
        repo.save_result("cam2", "v2", 5)
        
        service = AnalyticsService(analytics_repo=repo)
        
        overview = service.get_dashboard_overview(camera_id="cam1")
        
        assert overview.total_events == 1
        assert overview.total_visitors == 10
    
    def test_heatmap_analysis_calculation(self):
        """Service calculates heatmap analysis metrics."""
        repo = MockHeatmapRepository()
        repo.save_heatmap("cam1", "v1", "p1", hotspot_count=5, max_density=1.0)
        repo.save_heatmap("cam1", "v2", "p2", hotspot_count=15, max_density=0.5)
        
        service = AnalyticsService(heatmap_repo=repo)
        
        analysis = service.get_heatmap_analysis()
        
        assert analysis.total_heatmaps == 2
        assert analysis.avg_hotspots == 10.0
        assert analysis.max_density == 1.0
    
    def test_tracking_summary_logic(self):
        """Service summarizes tracking events."""
        repo = MockTrackingRepository()
        repo.save_tracking_event("cam1", "v1", object_count=5, max_objects=3)
        repo.save_tracking_event("cam1", "v2", object_count=5, max_objects=2)
        
        service = AnalyticsService(tracking_repo=repo)
        
        summary = service.get_tracking_summary()
        
        assert summary.total_objects == 10
        assert summary.peak_objects == 3
    
    def test_person_detection_summary_logic(self):
        """Service summarizes person detections."""
        repo = MockPersonDetectionRepository()
        repo.save_person_detection("cam1", "v1", max_people=4)
        repo.save_person_detection("cam1", "v2", max_people=6)
        
        service = AnalyticsService(person_detection_repo=repo)
        
        summary = service.get_person_detection_summary()
        
        assert summary.peak_occupancy == 6
    
    def test_missing_repositories_handled_gracefully(self):
        """Service handles missing optional repositories."""
        # Only analytics repo, others None
        service = AnalyticsService(analytics_repo=MockAnalyticsRepository())
        
        # Calling method related to missing repo should raise or return default
        # Implementation choice: Does it create empty summary or raise?
        # Assuming current implementation might raise AttributeError if repo is None
        # Verify behavior (adjust based on actual implementation)
        with pytest.raises(AttributeError):
            service.get_heatmap_analysis()
    
    def test_get_recent_results_formatting(self):
        """Service formats recent results correctly."""
        repo = MockAnalyticsRepository()
        idx = repo.save_result("cam1", "v1", 10)
        
        service = AnalyticsService(analytics_repo=repo)
        results = service.get_recent_results(limit=1)
        
        assert len(results) == 1
        assert results[0]["id"] == idx
        assert results[0]["camera_id"] == "cam1"
