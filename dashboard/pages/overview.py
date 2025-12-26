"""
Overview Page
=============
Main dashboard overview page with core analytics.
"""

import streamlit as st
from typing import Optional

# Try to use new architecture, fall back to legacy
try:
    from services.analytics_service import AnalyticsService
    HAS_NEW_ARCH = True
except ImportError:
    HAS_NEW_ARCH = False

from dashboard.components.metrics import (
    render_overview_metrics,
    render_hourly_chart,
    render_camera_grid,
    render_data_table
)


def render_overview_page(
    service: 'AnalyticsService' = None,
    camera_filter: Optional[str] = None,
    hours_filter: int = 24,
    # Legacy parameters for backward compatibility
    get_stats_fn=None,
    get_cameras_fn=None,
    get_hourly_fn=None,
    get_results_fn=None,
    db_path=None
):
    """
    Render the overview page.
    
    Args:
        service: AnalyticsService instance (new architecture)
        camera_filter: Optional camera ID filter
        hours_filter: Hours of data to display
        get_*_fn: Legacy function references for backward compatibility
        db_path: Legacy database path
    """
    
    # Get data - try new service first, then legacy
    if service and HAS_NEW_ARCH:
        overview = service.get_dashboard_overview(camera_filter, hours_filter)
        stats = {
            "total_events": overview.total_events,
            "total_visitors": overview.total_visitors,
            "avg_confidence": overview.avg_confidence,
            "motion_events": overview.motion_events
        }
        cameras = overview.cameras
        hourly_data = overview.hourly_data
        results = service.get_recent_results(limit=100, camera_id=camera_filter)
    else:
        # Legacy fallback
        stats = get_stats_fn(db_path, camera_id=camera_filter) if get_stats_fn else {}
        cameras = get_cameras_fn(db_path) if get_cameras_fn else []
        hourly_data = get_hourly_fn(db_path, hours=hours_filter, camera_id=camera_filter) if get_hourly_fn else []
        results = get_results_fn(db_path, limit=100, camera_id=camera_filter) if get_results_fn else []
    
    # Render camera overview if multiple cameras
    if not camera_filter:
        render_camera_grid(cameras)
    
    # Show selected camera info
    if camera_filter and cameras:
        cam_info = next((c for c in cameras if c.get('camera_id') == camera_filter), None)
        if cam_info:
            st.info(f"📹 **{cam_info.get('camera_name', '')}** - {cam_info.get('camera_location', '')}")
    
    # Metrics row
    render_overview_metrics(stats)
    st.divider()
    
    # Charts section
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        render_hourly_chart(hourly_data)
    
    with col_right:
        st.subheader("📋 Recent Events")
        if results:
            for result in results[:5]:
                camera_display = result.get('camera_name', result.get('camera_id', 'Unknown'))
                st.markdown(f"""
                **{camera_display}**  
                {result.get('filename', '')[:30]}...  
                👥 {result.get('visitor_count', 0)} visitors | 
                🎯 {result.get('confidence', 0):.0%} confidence  
                🕐 {str(result.get('timestamp', ''))[:16]}
                """)
                st.divider()
        else:
            st.info("No events recorded yet.")
    
    # Full data table
    st.divider()
    st.subheader("📑 All Data")
    display_cols = [
        "timestamp", "camera_name", "camera_location", 
        "filename", "visitor_count", "motion_detected", "confidence"
    ]
    render_data_table(results, display_cols)
