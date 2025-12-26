"""
Result Data Classes
====================
Standardized result types for all ML model outputs.
Using dataclasses for type safety and serialization.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
import json


@dataclass
class BaseResult:
    """Base class for all ML model results."""
    camera_id: str
    filename: str
    timestamp: datetime = field(default_factory=datetime.now)
    camera_name: str = ""
    camera_location: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def get_result_type(cls) -> str:
        """Return the result type identifier."""
        return 'base'


@dataclass
class AnalyticsResult(BaseResult):
    """Result for general video analytics."""
    visitor_count: int = 0
    motion_detected: bool = False
    confidence: float = 0.0
    
    @classmethod
    def get_result_type(cls) -> str:
        return 'analytics'


@dataclass
class HeatmapResult(BaseResult):
    """Result for heatmap generation."""
    heatmap_path: str = ""
    hotspot_count: int = 0
    max_density: float = 0.0
    avg_motion: float = 0.0
    grid_data: str = "{}"  # JSON string of grid data
    
    @classmethod
    def get_result_type(cls) -> str:
        return 'heatmap'
    
    def get_grid_data(self) -> Dict[str, Any]:
        """Parse grid data from JSON string."""
        try:
            return json.loads(self.grid_data)
        except (json.JSONDecodeError, TypeError):
            return {}


@dataclass
class TrackingResult(BaseResult):
    """Result for object tracking."""
    object_count: int = 0
    trajectories: str = ""  # JSON string of trajectory data
    avg_speed: float = 0.0
    max_objects: int = 0
    entries: int = 0
    exits: int = 0
    
    @classmethod
    def get_result_type(cls) -> str:
        return 'tracking'
    
    def get_trajectories(self) -> List[Dict[str, Any]]:
        """Parse trajectories from JSON string."""
        try:
            return json.loads(self.trajectories)
        except (json.JSONDecodeError, TypeError):
            return []


@dataclass  
class PersonDetectionResult(BaseResult):
    """Result for person detection."""
    total_detections: int = 0
    max_people: int = 0
    avg_people: float = 0.0
    detections_json: str = "[]"  # JSON string of per-frame detections
    
    @classmethod
    def get_result_type(cls) -> str:
        return 'person_detection'
    
    def get_detections(self) -> List[Dict[str, Any]]:
        """Parse detections from JSON string."""
        try:
            return json.loads(self.detections_json)
        except (json.JSONDecodeError, TypeError):
            return []


# Result type registry for dynamic lookup
RESULT_TYPES: Dict[str, type] = {
    'analytics': AnalyticsResult,
    'heatmap': HeatmapResult,
    'tracking': TrackingResult,
    'person_detection': PersonDetectionResult
}


def get_result_class(result_type: str) -> type:
    """Get the result class for a given type identifier."""
    return RESULT_TYPES.get(result_type, BaseResult)
