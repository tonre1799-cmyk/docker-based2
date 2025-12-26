"""
Repository Interfaces
=====================
Abstract base classes for all data access operations.
Implementations should be in the infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class BaseRepository(ABC):
    """Base repository interface with common operations."""
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the repository connection is healthy."""
        pass
    
    @abstractmethod
    def init_schema(self) -> None:
        """Initialize the database schema if needed."""
        pass


class AnalyticsRepository(BaseRepository):
    """
    Repository interface for core analytics operations.
    Handles general video processing results.
    """
    
    @abstractmethod
    def save_result(
        self,
        camera_id: str,
        filename: str,
        visitor_count: int,
        motion_detected: bool = False,
        confidence: float = 0.0,
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save an analytics result. Returns the record ID."""
        pass
    
    @abstractmethod
    def get_results(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve the latest analytics results."""
        pass
    
    @abstractmethod
    def get_stats(
        self,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get summary statistics.
        Returns: {total_events, total_visitors, avg_confidence, motion_events}
        """
        pass
    
    @abstractmethod
    def get_hourly_counts(
        self,
        hours: int = 24,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Get visitor counts grouped by hour.
        Returns: [{hour, visitors, events}, ...]
        """
        pass
    
    @abstractmethod
    def get_cameras(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """
        Get list of all cameras that have recorded data.
        Returns: [{camera_id, camera_name, camera_location, event_count, last_event}, ...]
        """
        pass


class HeatmapRepository(BaseRepository):
    """Repository interface for heatmap analytics."""
    
    @abstractmethod
    def save_heatmap(
        self,
        camera_id: str,
        filename: str,
        heatmap_path: str,
        hotspot_count: int = 0,
        max_density: float = 0.0,
        avg_motion: float = 0.0,
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save heatmap results. Returns the record ID."""
        pass
    
    @abstractmethod
    def get_heatmaps(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve heatmap results with optional date filtering."""
        pass
    
    @abstractmethod
    def get_heatmap_stats(
        self,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get heatmap statistics.
        Returns: {total_heatmaps, avg_hotspots, max_density, ...}
        """
        pass


class TrackingRepository(BaseRepository):
    """Repository interface for object tracking analytics."""
    
    @abstractmethod
    def save_tracking_event(
        self,
        camera_id: str,
        filename: str,
        object_count: int = 0,
        trajectories: str = "",
        avg_speed: float = 0.0,
        max_objects: int = 0,
        entries: int = 0,
        exits: int = 0,
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save tracking results. Returns the record ID."""
        pass
    
    @abstractmethod
    def get_tracking_events(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve tracking events."""
        pass
    
    @abstractmethod
    def get_tracking_stats(
        self,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get tracking statistics.
        Returns: {total_events, total_objects, avg_speed, peak_objects, ...}
        """
        pass


class PersonDetectionRepository(BaseRepository):
    """Repository interface for person detection analytics."""
    
    @abstractmethod
    def save_person_detection(
        self,
        camera_id: str,
        filename: str,
        total_detections: int = 0,
        max_people: int = 0,
        avg_people: float = 0.0,
        detections_json: str = "",
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save person detection results. Returns the record ID."""
        pass
    
    @abstractmethod
    def get_person_detections(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve person detection results."""
        pass
    
    @abstractmethod
    def get_person_detection_stats(
        self,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Get person detection statistics.
        Returns: {total_videos, total_detections, peak_occupancy, avg_people, ...}
        """
        pass


class CameraRepository(BaseRepository):
    """Repository interface for camera management."""
    
    @abstractmethod
    def save_camera(
        self,
        camera_id: str,
        name: str,
        location: str,
        ip: str,
        port: int = 81,
        enabled: bool = True,
        tenant_id: str = "default"
    ) -> str:
        """Save or update camera. Returns camera ID."""
        pass
    
    @abstractmethod
    def get_camera(self, camera_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """Get camera by ID."""
        pass
    
    @abstractmethod
    def list_cameras(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """List all cameras."""
        pass
    
    @abstractmethod
    def delete_camera(self, camera_id: str, tenant_id: str = "default") -> bool:
        """Delete camera. Returns True if deleted."""
        pass


class ProcessedFilesRepository(ABC):
    """Repository interface for tracking processed files."""
    
    @abstractmethod
    def is_processed(self, filename: str, tenant_id: str = "default") -> bool:
        """Check if a file has already been processed."""
        pass
    
    @abstractmethod
    def mark_processed(
        self,
        filename: str,
        camera_id: str,
        tenant_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Mark a file as processed. Returns True if successfully marked (atomic)."""
        pass
