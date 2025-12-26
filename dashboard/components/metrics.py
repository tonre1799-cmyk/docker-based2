"""
Dashboard Metrics Component
===========================
Reusable metric cards and data visualization components.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import pandas as pd


def render_metric_row(metrics: List[Dict[str, Any]], columns: int = 4):
    """
    Render a row of metric cards.
    
    Args:
        metrics: List of {label, value, icon, delta} dicts
        columns: Number of columns
    """
    cols = st.columns(columns)
    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            delta = metric.get('delta')
            st.metric(
                label=f"{metric.get('icon', '')} {metric['label']}",
                value=metric['value'],
                delta=delta
            )


def render_overview_metrics(stats: Dict[str, Any]):
    """Render overview metrics row."""
    metrics = [
        {"icon": "📊", "label": "Total Events", "value": stats.get("total_events", 0)},
        {"icon": "👥", "label": "Total Visitors", "value": stats.get("total_visitors", 0)},
        {"icon": "🎯", "label": "Avg Confidence", "value": f"{stats.get('avg_confidence', 0):.0%}"},
        {"icon": "🏃", "label": "Motion Events", "value": stats.get("motion_events", 0)}
    ]
    render_metric_row(metrics)


def render_person_detection_metrics(stats: Dict[str, Any]):
    """Render person detection metrics row."""
    metrics = [
        {"icon": "📹", "label": "Total Videos", "value": stats.get("total_videos", 0)},
        {"icon": "🔍", "label": "Total Detections", "value": stats.get("total_detections", 0)},
        {"icon": "👥", "label": "Peak Occupancy", "value": stats.get("peak_occupancy", 0)},
        {"icon": "📊", "label": "Avg People", "value": f"{stats.get('avg_people', 0):.1f}"}
    ]
    render_metric_row(metrics)


def render_tracking_metrics(stats: Dict[str, Any]):
    """Render tracking metrics row."""
    metrics = [
        {"icon": "📍", "label": "Total Events", "value": stats.get("total_events", 0)},
        {"icon": "🎯", "label": "Objects Tracked", "value": stats.get("total_objects", 0)},
        {"icon": "💨", "label": "Avg Speed", "value": f"{stats.get('avg_speed', 0):.1f} px/frame"},
        {"icon": "📈", "label": "Peak Objects", "value": stats.get("peak_objects", 0)}
    ]
    render_metric_row(metrics)


def render_heatmap_metrics(stats: Dict[str, Any]):
    """Render heatmap metrics row."""
    metrics = [
        {"icon": "🔥", "label": "Total Heatmaps", "value": stats.get("total_heatmaps", 0)},
        {"icon": "⚡", "label": "Avg Hotspots", "value": f"{stats.get('avg_hotspots', 0):.1f}"},
        {"icon": "📊", "label": "Max Density", "value": f"{stats.get('max_density', 0):.2f}"},
        {"icon": "🏃", "label": "Avg Motion", "value": f"{stats.get('avg_motion', 0):.2f}"}
    ]
    render_metric_row(metrics)


def render_data_table(data: List[Dict[str, Any]], columns: List[str] = None):
    """
    Render a data table with specified columns.
    
    Args:
        data: List of dictionaries
        columns: Columns to display (None = all)
    """
    if not data:
        st.info("No data available.")
        return
    
    df = pd.DataFrame(data)
    if columns:
        available_cols = [c for c in columns if c in df.columns]
        df = df[available_cols]
    
    st.dataframe(df, use_container_width=True)


def render_hourly_chart(hourly_data: List[Dict[str, Any]], title: str = "📈 Visitors Over Time"):
    """Render hourly visitor chart."""
    st.subheader(title)
    
    if not hourly_data:
        st.info("No hourly data available yet.")
        return
    
    df = pd.DataFrame(hourly_data)
    st.bar_chart(df.set_index("hour")["visitors"])


def render_camera_grid(cameras: List[Dict[str, Any]], max_columns: int = 3):
    """
    Render camera overview grid.
    
    Args:
        cameras: List of camera info dicts
        max_columns: Maximum columns per row
    """
    if not cameras or len(cameras) <= 1:
        return
    
    st.subheader("📹 Camera Overview")
    cols = st.columns(min(max_columns, len(cameras)))
    
    for idx, cam in enumerate(cameras):
        with cols[idx % max_columns]:
            st.markdown(f"**{cam.get('camera_name', cam.get('camera_id', 'Unknown'))}**")
            st.caption(f"📍 {cam.get('camera_location', 'Unknown')}")
            st.metric("Events", cam.get('event_count', 0))
            last_event = cam.get('last_event', '')
            st.caption(f"Last: {last_event[:16] if last_event else 'N/A'}")
    
    st.divider()
