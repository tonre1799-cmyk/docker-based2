import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from pathlib import Path
from infrastructure.repositories import get_repository
from core.cache_service import get_cache

cache = get_cache()

class AnalyticsService:
    """
    Service layer for dashboard analytics.
    Provides a clean interface for UI components and implements caching.
    """
    
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self.repo = get_repository()

    @st.cache_data(ttl=60)
    @cache.cache(key_prefix="analytics:overview", ttl=60)
    def get_overview_stats(self, hours: int = 24, camera_id: Optional[str] = None):
        """Get high-level statistics for the dashboard."""
        return self.repo.get_stats(camera_id=camera_id, tenant_id=self.tenant_id)

    @st.cache_data(ttl=60)
    @cache.cache(key_prefix="analytics:hourly", ttl=60)
    def get_hourly_data(self, hours: int = 24, camera_id: Optional[str] = None):
        """Get hourly activity data for charts."""
        data = self.repo.get_hourly_counts(hours=hours, camera_id=camera_id, tenant_id=self.tenant_id)
        if not data:
            return pd.DataFrame(columns=['hour', 'visitor_count'])
        return pd.DataFrame(data)

    @st.cache_data(ttl=60)
    @cache.cache(key_prefix="analytics:paginated", ttl=30)
    def get_paginated_results(self, page: int = 1, page_size: int = 10, camera_id: Optional[str] = None):
        """Get paginated analytics results with total count."""
        offset = (page - 1) * page_size
        results = self.repo.get_results(limit=page_size, camera_id=camera_id, tenant_id=self.tenant_id)
        total_count = self.repo.get_results_count(camera_id=camera_id, tenant_id=self.tenant_id)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "results": results,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    @st.cache_data(ttl=300)
    def get_available_cameras(self):
        """Get list of active cameras."""
        return self.repo.get_cameras(tenant_id=self.tenant_id)

    @st.cache_data(ttl=60)
    def get_camera_performance(self):
        """Get performance metrics per camera."""
        return self.repo.get_camera_stats(tenant_id=self.tenant_id)

    @st.cache_data(ttl=120)
    def get_latest_heatmaps(self, limit: int = 10, camera_id: Optional[str] = None):
        """Get latest generated heatmaps."""
        return self.repo.get_heatmaps(limit=limit, camera_id=camera_id, tenant_id=self.tenant_id)

    @st.cache_data(ttl=60)
    def get_tracking_analytics(self, hours: int = 24):
        """Get detailed tracking and visitor analytics."""
        return self.repo.get_tracking_stats(tenant_id=self.tenant_id)

    @st.cache_data(ttl=60)
    def get_person_analytics(self, hours: int = 24):
        """Get person detection statistics."""
        return self.repo.get_person_detection_stats(tenant_id=self.tenant_id)

def get_analytics_service() -> AnalyticsService:
    """Factory to get the analytics service with current tenant context."""
    # In a real multi-tenant app, we would get this from the session/JWT
    tenant_id = st.session_state.get("tenant_id", "default")
    return AnalyticsService(tenant_id=tenant_id)
