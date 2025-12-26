"""
Test Dashboard Components (Phase E)
===================================
Test reusable UI components.
"""

import pytest
from unittest.mock import patch
from dashboard.components.metrics import render_metric_row


class TestMetricsComponent:
    """Test metric rendering."""
    
    def test_render_metric_row(self):
        """Renders correct number of metrics."""
        metrics = [
            {"label": "Test", "value": 10},
            {"label": "Test 2", "value": 20}
        ]
        
        # Mock streamlit columns and metric
        with patch("streamlit.columns") as mock_cols, \
             patch("streamlit.metric") as mock_metric:
            
            # Setup context manager mock for cols
            mock_cols.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
            
            render_metric_row(metrics)
            
            assert mock_metric.call_count == 2
