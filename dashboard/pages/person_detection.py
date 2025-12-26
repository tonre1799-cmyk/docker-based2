"""
Person Detection Page
=====================
Person detection analysis page.
"""

import streamlit as st
from typing import Optional

from dashboard.components.metrics import render_person_detection_metrics, render_data_table


def render_person_detection_page(
    service=None,
    camera_filter: Optional[str] = None,
    # Legacy parameters
    get_person_detection_stats_fn=None,
    get_person_detections_fn=None,
    db_path=None
):
    """
    Render the person detection analysis page.
    
    Args:
        service: AnalyticsService instance
        camera_filter: Optional camera ID filter
        get_*_fn: Legacy function references
        db_path: Legacy database path
    """
    st.header("👥 Person Detection Analysis")
    
    # Get stats and detections
    if service:
        summary = service.get_person_detection_summary(camera_id=camera_filter, recent_limit=20)
        stats = {
            "total_videos": summary.total_videos,
            "total_detections": summary.total_detections,
            "peak_occupancy": summary.peak_occupancy,
            "avg_people": summary.avg_people
        }
        detections = summary.recent_detections
    else:
        # Legacy fallback
        stats = get_person_detection_stats_fn(db_path, camera_id=camera_filter) if get_person_detection_stats_fn else {}
        detections = get_person_detections_fn(db_path, limit=20, camera_id=camera_filter) if get_person_detections_fn else []
    
    # Render metrics
    render_person_detection_metrics(stats)
    st.divider()
    
    # Recent detections table
    st.subheader("Recent Person Detections")
    display_cols = [
        'timestamp', 'camera_name', 'filename',
        'total_detections', 'max_people', 'avg_people'
    ]
    render_data_table(detections, display_cols)
