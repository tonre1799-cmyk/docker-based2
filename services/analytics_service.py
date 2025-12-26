"""
Analytics Service
=================
Central service for all analytics queries.
Used by dashboards, APIs, and reports.
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from core.interfaces.repository import (
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository
)

logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    """Date range for filtering queries."""
    start: date
    end: date


@dataclass
class DashboardOverview:
    """Overview data for dashboard main page."""
    total_events: int
    total_visitors: int
    avg_confidence: float
    motion_events: int
    cameras: List[Dict[str, Any]]
    hourly_data: List[Dict[str, Any]]


@dataclass
class HeatmapAnalysis:
    """Heatmap analysis data."""
    total_heatmaps: int
    avg_hotspots: float
    max_density: float
    avg_motion: float
    heatmap_paths: List[str]


@dataclass
class TrackingSummary:
    """Tracking summary data."""
    total_events: int
    total_objects: int
    avg_speed: float
    peak_objects: int
    total_entries: int
    total_exits: int
    recent_events: List[Dict[str, Any]]


@dataclass
class PersonDetectionSummary:
    """Person detection summary data."""
    total_videos: int
    total_detections: int
    peak_occupancy: int
    avg_people: float
    recent_detections: List[Dict[str, Any]]


class AnalyticsService:
    """
    Service layer for analytics data access.
    
    Aggregates multiple repositories and provides
    high-level methods for dashboard and API consumption.
    """
    
    def __init__(
        self,
        analytics_repo: AnalyticsRepository,
        heatmap_repo: HeatmapRepository = None,
        tracking_repo: TrackingRepository = None,
        person_detection_repo: PersonDetectionRepository = None
    ):
        """
        Initialize with repository implementations.
        
        In most cases, a single PostgresRepository implements all interfaces,
        so you can pass the same instance to all parameters.
        """
        self.analytics = analytics_repo
        self.heatmaps = heatmap_repo or analytics_repo
        self.tracking = tracking_repo or analytics_repo
        self.person_detection = person_detection_repo or analytics_repo
    
    def health_check(self) -> bool:
        """Check if all repositories are healthy."""
        return self.analytics.health_check()
    
    def get_dashboard_overview(
        self,
        camera_id: Optional[str] = None,
        hours: int = 24
    ) -> DashboardOverview:
        """
        Get overview data for the main dashboard.
        
        Args:
            camera_id: Optional camera filter
            hours: Hours of data to include in hourly chart
            
        Returns:
            DashboardOverview with stats, cameras, and hourly data
        """
        stats = self.analytics.get_stats(camera_id)
        cameras = self.analytics.get_cameras()
        hourly = self.analytics.get_hourly_counts(hours, camera_id)
        
        return DashboardOverview(
            total_events=stats.get('total_events', 0),
            total_visitors=stats.get('total_visitors', 0),
            avg_confidence=stats.get('avg_confidence', 0.0),
            motion_events=stats.get('motion_events', 0),
            cameras=cameras,
            hourly_data=hourly
        )
    
    def get_recent_results(
        self,
        limit: int = 10,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent analytics results."""
        return self.analytics.get_results(limit, camera_id)
    
    def get_heatmap_analysis(
        self,
        date_range: Optional[DateRange] = None,
        camera_id: Optional[str] = None
    ) -> HeatmapAnalysis:
        """
        Get heatmap analysis data.
        
        Args:
            date_range: Optional date range filter
            camera_id: Optional camera filter
            
        Returns:
            HeatmapAnalysis with stats and paths
        """
        stats = self.heatmaps.get_heatmap_stats(camera_id)
        
        # Get heatmap paths for aggregation
        start_date = datetime.combine(date_range.start, datetime.min.time()) if date_range else None
        end_date = datetime.combine(date_range.end, datetime.max.time()) if date_range else None
        
        heatmaps = self.heatmaps.get_heatmaps(
            limit=1000,
            camera_id=camera_id,
            start_date=start_date,
            end_date=end_date
        )
        
        paths = [h.get('heatmap_path', '') for h in heatmaps if h.get('heatmap_path')]
        
        return HeatmapAnalysis(
            total_heatmaps=stats.get('total_heatmaps', 0),
            avg_hotspots=stats.get('avg_hotspots', 0.0),
            max_density=stats.get('max_density', 0.0),
            avg_motion=stats.get('avg_motion', 0.0),
            heatmap_paths=paths
        )
    
    def get_tracking_summary(
        self,
        camera_id: Optional[str] = None,
        recent_limit: int = 20
    ) -> TrackingSummary:
        """
        Get tracking summary data.
        
        Args:
            camera_id: Optional camera filter
            recent_limit: Number of recent events to include
            
        Returns:
            TrackingSummary with stats and recent events
        """
        stats = self.tracking.get_tracking_stats(camera_id)
        events = self.tracking.get_tracking_events(recent_limit, camera_id)
        
        return TrackingSummary(
            total_events=stats.get('total_events', 0),
            total_objects=stats.get('total_objects', 0),
            avg_speed=stats.get('avg_speed', 0.0),
            peak_objects=stats.get('peak_objects', 0),
            total_entries=stats.get('total_entries', 0),
            total_exits=stats.get('total_exits', 0),
            recent_events=events
        )
    
    def get_person_detection_summary(
        self,
        camera_id: Optional[str] = None,
        recent_limit: int = 20
    ) -> PersonDetectionSummary:
        """
        Get person detection summary data.
        
        Args:
            camera_id: Optional camera filter
            recent_limit: Number of recent detections to include
            
        Returns:
            PersonDetectionSummary with stats and recent detections
        """
        stats = self.person_detection.get_person_detection_stats(camera_id)
        detections = self.person_detection.get_person_detections(recent_limit, camera_id)
        
        return PersonDetectionSummary(
            total_videos=stats.get('total_videos', 0),
            total_detections=stats.get('total_detections', 0),
            peak_occupancy=stats.get('peak_occupancy', 0),
            avg_people=stats.get('avg_people', 0.0),
            recent_detections=detections
        )
    
    def get_camera_list(self) -> List[Dict[str, Any]]:
        """Get list of all cameras with recorded data."""
        return self.analytics.get_cameras()
