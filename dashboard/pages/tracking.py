"""
Tracking Page
=============
Object tracking analysis page.
"""

import streamlit as st
from typing import Optional

from dashboard.components.metrics import render_tracking_metrics, render_data_table


def render_tracking_page(
    service=None,
    camera_filter: Optional[str] = None,
    # Legacy parameters
    get_tracking_stats_fn=None,
    get_tracking_events_fn=None,
    db_path=None
):
    """
    Render the tracking analysis page.
    
    Args:
        service: AnalyticsService instance
        camera_filter: Optional camera ID filter
        get_*_fn: Legacy function references
        db_path: Legacy database path
    """
    st.header("📍 Object Tracking Analysis")
    
    # Get stats and events
    if service:
        summary = service.get_tracking_summary(camera_id=camera_filter, recent_limit=20)
        stats = {
            "total_events": summary.total_events,
            "total_objects": summary.total_objects,
            "avg_speed": summary.avg_speed,
            "peak_objects": summary.peak_objects
        }
        events = summary.recent_events
    else:
        # Legacy fallback
        stats = get_tracking_stats_fn(db_path, camera_id=camera_filter) if get_tracking_stats_fn else {}
        events = get_tracking_events_fn(db_path, limit=20, camera_id=camera_filter) if get_tracking_events_fn else []
    
    # Render metrics
    render_tracking_metrics(stats)
    st.divider()
    
    # Recent events table
    st.subheader("Recent Tracking Events")
    display_cols = [
        'timestamp', 'camera_name', 'filename', 
        'object_count', 'avg_speed', 'max_objects'
    ]
    render_data_table(events, display_cols)
