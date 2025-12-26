"""
Dashboard Filters Component
===========================
Sidebar filters for camera selection and time ranges.
"""

import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import datetime


def render_sidebar_filters(
    cameras: List[Dict[str, Any]] = None,
    show_refresh: bool = True,
    show_hours: bool = True
) -> Dict[str, Any]:
    """
    Render sidebar filters and return selected values.
    
    Args:
        cameras: List of camera dicts for camera selector
        show_refresh: Whether to show refresh controls
        show_hours: Whether to show hours filter
        
    Returns:
        Dict with filter values: {auto_refresh, refresh_interval, hours_filter, camera_filter}
    """
    filters = {}
    
    with st.sidebar:
        st.header("⚙️ Settings")
        
        if show_refresh:
            filters['auto_refresh'] = st.checkbox("Auto-refresh", value=True)
            filters['refresh_interval'] = st.slider(
                "Refresh interval (seconds)", 5, 60, 10
            )
        
        st.divider()
        st.header("📊 Filters")
        
        if show_hours:
            filters['hours_filter'] = st.slider(
                "Show data from last N hours", 1, 168, 24
            )
        
        # Camera filter
        filters['camera_filter'] = None
        if cameras:
            camera_options = ["All Cameras"] + [
                f"{cam.get('camera_name', cam.get('camera_id'))} ({cam.get('camera_id')})"
                for cam in cameras
            ]
            selected = st.selectbox("📹 Camera", camera_options)
            
            if selected != "All Cameras":
                idx = camera_options.index(selected) - 1
                filters['camera_filter'] = cameras[idx].get('camera_id')
        
        st.divider()
        
        if show_refresh and st.button("🔄 Refresh Now"):
            st.rerun()
    
    return filters


def render_date_range_filter(
    default_days: int = 7,
    key_prefix: str = ""
) -> Tuple[datetime.date, datetime.date]:
    """
    Render date range selector.
    
    Args:
        default_days: Default number of days to look back
        key_prefix: Prefix for widget keys
        
    Returns:
        Tuple of (start_date, end_date)
    """
    today = datetime.date.today()
    default_start = today - datetime.timedelta(days=default_days)
    
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.date_input(
            "📅 Select Date Range",
            value=(default_start, today),
            max_value=today,
            key=f"{key_prefix}_date_range"
        )
    
    start_date = date_range[0]
    end_date = date_range[1] if len(date_range) > 1 else start_date
    
    return start_date, end_date


def render_sidebar_info(db_path: str = None, db_exists: bool = True):
    """Render sidebar database info."""
    with st.sidebar:
        st.divider()
        if db_path:
            st.caption(f"Database: {db_path}")
        st.caption(f"Connected: {'✅' if db_exists else '❌'}")
