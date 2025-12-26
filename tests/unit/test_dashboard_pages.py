"""
Test Dashboard Pages (Phase E)
==============================
Test dashboard page rendering with mocked services.
"""

import pytest
from unittest.mock import MagicMock
from dashboard.pages.overview import render_overview_page
from services.analytics_service import DashboardOverview


class TestOverviewPage:
    """Test Overview page rendering logic."""
    
    def test_render_with_new_service(self):
        """Page renders using AnalyticsService data."""
        # Mock service
        service = MagicMock()
        overview = DashboardOverview(
            total_events=100,
            total_visitors=50,
            avg_confidence=0.9,
            motion_events=5,
            cameras=[],
            hourly_data=[]
        )
        service.get_dashboard_overview.return_value = overview
        service.get_recent_results.return_value = []
        
        # Mock streamlit to prevent actual rendering
        with patch("dashboard.pages.overview.st") as mock_st, \
             patch("dashboard.pages.overview.render_overview_metrics") as mock_metrics, \
             patch("dashboard.pages.overview.render_hourly_chart"), \
             patch("dashboard.pages.overview.render_camera_grid"):
            
            render_overview_page(service=service)
            
            # Verify metrics called with correct data
            mock_metrics.assert_called_once()
            stats = mock_metrics.call_args[0][0]
            assert stats["total_events"] == 100
            assert stats["total_visitors"] == 50

    def test_render_legacy_fallback(self):
        """Page falls back to legacy functions if service is None."""
        mock_stats_fn = MagicMock(return_value={"total_events": 10})
        
        with patch("dashboard.pages.overview.st"), \
             patch("dashboard.pages.overview.render_overview_metrics") as mock_metrics, \
             patch("dashboard.pages.overview.HAS_NEW_ARCH", False):
            
            render_overview_page(
                service=None, 
                get_stats_fn=mock_stats_fn,
                db_path="test.db"
            )
            
            mock_stats_fn.assert_called_once()
            stats = mock_metrics.call_args[0][0]
            assert stats["total_events"] == 10
