"""
Heatmap Page
============
Heatmap analysis page with aggregation support.
"""

import streamlit as st
from pathlib import Path
from typing import Optional, List
import datetime

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from dashboard.components.metrics import render_heatmap_metrics
from dashboard.components.filters import render_date_range_filter


def render_heatmap_page(
    service=None,
    camera_filter: Optional[str] = None,
    # Legacy parameters
    get_heatmap_stats_fn=None,
    get_heatmaps_fn=None,
    db_path=None
):
    """
    Render the heatmap analysis page.
    
    Args:
        service: AnalyticsService instance
        camera_filter: Optional camera ID filter
        get_*_fn: Legacy function references
        db_path: Legacy database path
    """
    st.header("🔥 Motion Heatmap Analysis")
    
    # Date range filter
    start_date, end_date = render_date_range_filter(default_days=7, key_prefix="heatmap")
    st.divider()
    
    # Get stats
    if service:
        from services.analytics_service import DateRange
        analysis = service.get_heatmap_analysis(
            date_range=DateRange(start=start_date, end=end_date),
            camera_id=camera_filter
        )
        stats = {
            "total_heatmaps": analysis.total_heatmaps,
            "avg_hotspots": analysis.avg_hotspots,
            "max_density": analysis.max_density,
            "avg_motion": analysis.avg_motion
        }
        heatmap_paths = analysis.heatmap_paths
    else:
        # Legacy fallback
        stats = get_heatmap_stats_fn(db_path, camera_id=camera_filter) if get_heatmap_stats_fn else {}
        heatmaps = get_heatmaps_fn(db_path, limit=1000, camera_id=camera_filter) if get_heatmaps_fn else []
        heatmap_paths = [h.get('heatmap_path', '') for h in heatmaps if h.get('heatmap_path')]
    
    # Render metrics
    render_heatmap_metrics(stats)
    st.divider()
    
    # Aggregated heatmap
    st.subheader(f"Combined Heatmap ({start_date} to {end_date})")
    
    if not heatmap_paths:
        st.info("No heatmaps found for this period.")
        return
    
    if not HAS_CV2:
        st.warning("OpenCV not available for heatmap aggregation.")
        return
    
    # Filter to valid paths
    valid_paths = [Path(p) for p in heatmap_paths if Path(p).exists()]
    
    if not valid_paths:
        st.warning("Heatmap records found in DB but files are missing from disk.")
        return
    
    st.write(f"Blending {len(valid_paths)} heatmaps...")
    
    # Load and blend heatmaps
    first_img = cv2.imread(str(valid_paths[0]), cv2.IMREAD_UNCHANGED)
    if first_img is None:
        st.error("Error loading first heatmap.")
        return
    
    accumulator = np.zeros(first_img.shape, dtype=np.float32)
    count = 0
    
    for p in valid_paths:
        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if img is not None and img.shape == accumulator.shape:
            accumulator = cv2.add(accumulator, img.astype(np.float32))
            count += 1
    
    if count > 0:
        result = (accumulator / count).astype(np.uint8)
        
        # Convert color space for Streamlit
        if len(result.shape) == 3:
            if result.shape[2] == 4:
                result = cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA)
            else:
                result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        
        st.image(
            result,
            caption=f"Aggregated heatmap ({start_date} to {end_date})",
            use_container_width=True
        )
