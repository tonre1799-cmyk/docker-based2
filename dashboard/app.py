"""
ESP32-CAM Analytics Dashboard
=============================
Streamlit dashboard for visualizing video analytics.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
import time
import cv2 # Required for heatmap blending
import numpy as np
import yaml

def load_config():
    config_path = Path("/app/customer_config.yaml")
    default_config = {
        "customer": {"name": "ESP32-CAM Analytics"},
        "branding": {"page_title": "Analytics Dashboard", "theme_color": "#1e3a5f"},
        "features": {"heatmaps": True, "face_recognition": False}
    }
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            st.error(f"Error loading config: {e}")
    return default_config

APP_CONFIG = load_config()

from dashboard.services.analytics_service import get_analytics_service

# Initialize Service
analytics = get_analytics_service()


# ============================================
# Page Configuration
# ============================================
st.set_page_config(
    page_title=APP_CONFIG["branding"].get("page_title", "Analytics"),
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# Custom CSS
# ============================================
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: """ + APP_CONFIG["branding"].get("theme_color", "#1e3a5f") + """;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Header
# ============================================
st.markdown(f'<h1 class="main-header">📹 {APP_CONFIG["customer"].get("name", "ESP32-CAM")} Dashboard</h1>', unsafe_allow_html=True)

# Model tabs
tab_overview, tab_person, tab_heatmap, tab_tracking, tab_health = st.tabs(["📊 Overview", "👥 Person Detection", "🔥 Heatmap", "📍 Tracking", "💓 System Health"])

# ============================================
# Sidebar
# ============================================
with st.sidebar:
    st.header("⚙️ Settings")
    
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10)
    
    st.divider()
    
    st.header("📊 Filters")
    hours_filter = st.slider("Show data from last N hours", 1, 168, 24)
    
    # Camera filter
    cameras = analytics.get_available_cameras()
    if cameras:
        camera_options = ["All Cameras"] + [f"{cam['camera_name']} ({cam['camera_id']})" for cam in cameras]
        selected_camera = st.selectbox("📹 Camera", camera_options)
        
        if selected_camera == "All Cameras":
            camera_filter = None
        else:
            camera_filter = cameras[camera_options.index(selected_camera) - 1]["camera_id"]
    else:
        camera_filter = None
    
    st.divider()
    
    if st.button("🔄 Refresh Now"):
        st.rerun()
    
    st.divider()
    st.caption(f"Database: {DB_PATH}")
    st.caption(f"Exists: {DB_PATH.exists()}")

# ============================================
# Main Content
# ============================================

# Check if database exists
if not DB_PATH.exists():
    st.warning("⏳ Waiting for data... No recordings have been processed yet.")
    st.info("""
    **Getting Started:**
    1. Flash your ESP32-CAM with the firmware
    2. Configure the camera in Kerberos Agent UI (http://localhost:8080)
    3. Wait for recordings to be processed
    
    This dashboard will update automatically when data is available.
    """)
else:
    # Show camera overview if no filter selected
    if camera_filter is None:
        cameras = get_cameras(DB_PATH)
        if cameras and len(cameras) > 1:
            st.subheader("📹 Camera Overview")
            
            # Display cameras in a grid
            cols = st.columns(min(3, len(cameras)))
            for idx, cam in enumerate(cameras):
                with cols[idx % 3]:
                    st.markdown(f"**{cam['camera_name']}**")
                    st.caption(f"📍 {cam['camera_location']}")
                    st.metric("Events", cam['event_count'])
                    st.caption(f"Last: {cam['last_event'][:16] if cam['last_event'] else 'N/A'}")
            
            st.divider()
    
    # Fetch data using service
    stats = analytics.get_overview_stats(hours=hours_filter, camera_id=camera_filter)
    
    # Show camera info if filtered
    if camera_filter:
        cameras = get_cameras(DB_PATH)
        cam_info = next((c for c in cameras if c['camera_id'] == camera_filter), None)
        if cam_info:
            st.info(f"📹 **{cam_info['camera_name']}** - {cam_info['camera_location']}")
    
    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Events", stats["total_events"])
    
    with col2:
        st.metric("👥 Total Visitors", stats["total_visitors"])
    
    with col3:
        st.metric("🎯 Avg Confidence", f"{stats['avg_confidence']:.0%}")
    
    with col4:
        st.metric("🏃 Motion Events", stats["motion_events"])
    
    st.divider()
    
    # Charts
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        hourly_df = analytics.get_hourly_data(hours=hours_filter, camera_id=camera_filter)
        
        if not hourly_df.empty:
            st.bar_chart(hourly_df.set_index("hour")["visitor_count"])
        else:
            st.info("No hourly data available yet.")
    
    with col_right:
        st.subheader("📋 Recent Events")
        
        results = get_results(DB_PATH, limit=10, camera_id=camera_filter)
        
        if results:
            for result in results[:5]:
                with st.container():
                    camera_display = result.get('camera_name', result.get('camera_id', 'Unknown'))
                    st.markdown(f"""
                    **{camera_display}**  
                    {result['filename'][:30]}...  
                    👥 {result['visitor_count']} visitors | 
                    🎯 {result['confidence']:.0%} confidence  
                    🕐 {result['timestamp'][:16]}
                    """)
                    st.divider()
        else:
            st.info("No events recorded yet.")
    
    # Data Table with Pagination
    st.divider()
    st.subheader("📑 All Data")
    
    # Pagination session state
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1
    
    page_size = st.sidebar.select_slider("Results per page", options=[10, 20, 50, 100], value=20)
    
    # Fetch paginated data
    data = analytics.get_paginated_results(
        page=st.session_state.current_page, 
        page_size=page_size, 
        camera_id=camera_filter
    )
    
    pagination_info = f"Page {data['page']} of {data['total_pages']} (Total: {data['total_count']})"
    st.write(pagination_info)
    
    if data["results"]:
        df = pd.DataFrame(data["results"])
        display_cols = ["timestamp", "camera_name", "camera_location", "filename", "visitor_count", "motion_detected", "confidence"]
        available_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available_cols], use_container_width=True)
        
        # Pagination controls
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("⬅️ Previous", disabled=not data["has_prev"]):
                st.session_state.current_page -= 1
                st.rerun()
        with col_info:
            st.markdown(f"<p style='text-align: center;'>{pagination_info}</p>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next ➡️", disabled=not data["has_next"]):
                st.session_state.current_page += 1
                st.rerun()
    else:
        st.info("No data available.")

# ============================================
# HEATMAP TAB
# ============================================
with tab_heatmap:
    st.header("🔥 Motion Heatmap Analysis")
    
    if not DB_PATH.exists():
        st.warning("⏳ Waiting for heatmap data...")
    else:
        # Date Range Filter for Heatmap
        import datetime
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            date_range = st.date_input(
                "📅 Select Date Range",
                value=(default_start, today),
                max_value=today
            )
        
        start_date = date_range[0]
        end_date = date_range[1] if len(date_range) > 1 else start_date
        
        st.divider()
        
        # Get heatmap stats (filtered by date)
        # Note: We'll fetch raw rows to filter in python for now or update SQL query
        # Ideally, move this to database.py
        
        # Aggregation Logic
        st.subheader(f"Combined Heatmap ({start_date} to {end_date})")
        
        import cv2
        import numpy as np
        
        # Fetch all heatmaps in range
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT heatmap_path FROM analytics 
            WHERE date(timestamp) >= date(?) 
            AND date(timestamp) <= date(?)
            AND heatmap_path IS NOT NULL
        """
        params = [start_date.isoformat(), end_date.isoformat()]
        
        if camera_filter:
            query += " AND camera_id = ?"
            params.append(camera_filter)
            
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            st.info(f"No heatmaps found for this period.")
        else:
            heatmap_paths = [Path(row['heatmap_path']) for row in rows]
            valid_paths = [p for p in heatmap_paths if p.exists()]
            
            if valid_paths:
                st.write(f"Blending {len(valid_paths)} heatmaps...")
                
                # Load first image to get dimensions
                first_img = cv2.imread(str(valid_paths[0]), cv2.IMREAD_UNCHANGED)
                
                if first_img is None:
                     st.error("Error loading first heatmap.")
                else:
                    # Initialize accumulator (float for precision)
                    accumulator = np.zeros(first_img.shape, dtype=np.float32)
                    
                    count = 0
                    for p in valid_paths:
                        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
                        if img is not None and img.shape == accumulator.shape:
                            accumulator = cv2.add(accumulator, img.astype(np.float32))
                            count += 1
                    
                    if count > 0:
                        # Normalize back to 0-255
                        # Simple averaging for transparency
                        result = accumulator / count
                        result = result.astype(np.uint8)
                        
                        # Display
                        # OpenCV is BGR, Streamlit expects RGB
                        # But standard heatmaps are often just colored. If it has alpha:
                        if result.shape[2] == 4:
                             result = cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA)
                        else:
                             result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
                             
                        st.image(result, caption=f"aggregated_heatmap_{start_date}_{end_date}.png", use_container_width=True)
            else:
                 st.warning("Heatmap records found in DB but files are missing from disk.")

# ============================================
# PERSON DETECTION TAB
# ============================================
with tab_person:
    st.header("👥 Person Detection Analysis")
    
    if not DB_PATH.exists():
        st.warning("⏳ Waiting for person detection data...")
    else:
        pd_stats = analytics.get_person_analytics(hours=hours_filter)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Videos", pd_stats.get('total_videos', 0))
        with col2:
            st.metric("Total Detections", pd_stats.get('total_detections', 0))
        with col3:
            st.metric("Peak Occupancy", pd_stats.get('peak_occupancy', 0))
        with col4:
            st.metric("Avg People", f"{pd_stats.get('avg_people', 0.0):.1f}")
        
        st.divider()
        
        # Recent detections
        detections = get_person_detections(DB_PATH, limit=20, camera_id=camera_filter)
        
        if detections:
            st.subheader("Recent Person Detections")
            
            # Create dataframe
            df_person = pd.DataFrame(detections)
            display_cols = ['timestamp', 'camera_name', 'filename', 'total_detections', 'max_people', 'avg_people']
            available_cols = [c for c in display_cols if c in df_person.columns]
            
            st.dataframe(df_person[available_cols], use_container_width=True)
        else:
            st.info("No person detections recorded yet.")

# ============================================
# TRACKING TAB
# ============================================
with tab_tracking:
    st.header("📍 Object Tracking Analysis")
    
    if not DB_PATH.exists():
        st.warning("⏳ Waiting for tracking data...")
    else:
        # Get tracking stats
        tr_stats = get_tracking_stats(DB_PATH, camera_id=camera_filter)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Events", tr_stats.get('total_events', 0))
        with col2:
            st.metric("Objects Tracked", tr_stats.get('total_objects', 0))
        with col3:
            st.metric("Avg Speed", f"{tr_stats.get('avg_speed', 0):.1f} px/frame")
        with col4:
            st.metric("Peak Objects", tr_stats.get('peak_objects', 0))
        
        st.divider()
        
        # Recent tracking events
        events = get_tracking_events(DB_PATH, limit=20, camera_id=camera_filter)
        
        if events:
            st.subheader("Recent Tracking Events")
            
            # Create dataframe
            df_tracking = pd.DataFrame(events)
            display_cols = ['timestamp', 'camera_name', 'filename', 'object_count', 'avg_speed', 'max_objects']
            available_cols = [c for c in display_cols if c in df_tracking.columns]
            
            st.dataframe(df_tracking[available_cols], use_container_width=True)
        else:
            st.info("No tracking events recorded yet.")

# ============================================
# SYSTEM HEALTH TAB
# ============================================
with tab_health:
    st.header("💓 System Health & Observability")
    
    import requests
    
    def check_http_health(url, name):
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 200:
                st.success(f"✅ {name} is Healthy")
                return True
            else:
                st.error(f"❌ {name} is Unhealthy (Status: {resp.status_code})")
                return False
        except Exception as e:
            st.error(f"❌ {name} is Offline ({e})")
            return False

    col_h1, col_h2, col_h3 = st.columns(3)
    
    with col_h1:
        st.subheader("Services Status")
        # These URLs would be internal in Docker, but let's use the ones mapped or internal hosts
        # In Docker Compose, services can reach each other by name.
        # But Streamlit is in the same network, so it can use service names.
        check_http_health("http://dispatcher:5000/health", "Dispatcher")
        check_http_health("http://camera-api:8000/health", "Camera API")
        
        # ML Worker doesn't have HTTP, but we can check if it's reporting metrics
        check_http_health("http://ml_worker:9090", "ML Worker (Metrics Port)")

    with col_h2:
        st.subheader("Queue Status")
        # Try to get queue depth from Redis (internal host)
        import redis
        try:
            r = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=6379, decode_responses=True)
            q_len = r.llen("ml_processing_queue")
            st.metric("Redis Queue Depth", q_len)
            if q_len > 50:
                st.warning("⚠️ High queue depth detected. Workers may be lagging.")
        except Exception as e:
            st.error(f"Could not connect to Redis: {e}")

    with col_h3:
        st.subheader("Observability Links")
        st.markdown("""
        - [🔎 Jaeger Tracing](http://localhost:16686)
        - [📈 Prometheus Metrics](http://localhost:9090)
        - [📊 Grafana Dashboards](http://localhost:3000)
        """)
        st.info("Note: Links assume you are accessing via localhost.")

    st.divider()
    st.subheader("Logging Context")
    st.write("Ensuring all services are reporting with Trace IDs for correlation.")
    st.code("""
    {
      "event": "video_processed",
      "trace_id": "032x...",
      "span_id": "016x..."
    }
    """, language="json")

# ============================================
# Auto-refresh
# ============================================
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
