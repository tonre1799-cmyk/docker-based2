"""
Mock Repository Factories
=========================
In-memory implementations of repository interfaces for testing.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


class MockAnalyticsRepository:
    """
    In-memory mock of AnalyticsRepository.
    
    Use this to test services without a real database.
    """
    
    def __init__(self):
        self._results: List[Dict[str, Any]] = []
        self._next_id = 1
    
    def health_check(self) -> bool:
        return True
    
    def init_schema(self) -> None:
        pass
    
    def save_result(
        self,
        camera_id: str,
        filename: str,
        visitor_count: int,
        motion_detected: bool = False,
        confidence: float = 0.0,
        camera_name: str = "",
        camera_location: str = ""
    ) -> int:
        record = {
            "id": self._next_id,
            "camera_id": camera_id,
            "filename": filename,
            "visitor_count": visitor_count,
            "motion_detected": motion_detected,
            "confidence": confidence,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "timestamp": datetime.now()
        }
        self._results.append(record)
        self._next_id += 1
        return record["id"]
    
    def get_results(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self._results
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        return list(reversed(results[:limit]))
    
    def get_stats(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._results
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        
        if not results:
            return {
                "total_events": 0,
                "total_visitors": 0,
                "avg_confidence": 0.0,
                "motion_events": 0
            }
        
        return {
            "total_events": len(results),
            "total_visitors": sum(r["visitor_count"] for r in results),
            "avg_confidence": round(sum(r["confidence"] for r in results) / len(results), 2),
            "motion_events": sum(1 for r in results if r["motion_detected"])
        }
    
    def get_hourly_counts(
        self,
        hours: int = 24,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Simplified: return empty list for mock
        return []
    
    def get_cameras(self) -> List[Dict[str, Any]]:
        cameras = {}
        for r in self._results:
            cam_id = r["camera_id"]
            if cam_id not in cameras:
                cameras[cam_id] = {
                    "camera_id": cam_id,
                    "camera_name": r.get("camera_name", cam_id),
                    "camera_location": r.get("camera_location", ""),
                    "event_count": 0,
                    "last_event": r["timestamp"]
                }
            cameras[cam_id]["event_count"] += 1
            cameras[cam_id]["last_event"] = max(cameras[cam_id]["last_event"], r["timestamp"])
        return list(cameras.values())


class MockHeatmapRepository:
    """In-memory mock of HeatmapRepository."""
    
    def __init__(self):
        self._heatmaps: List[Dict[str, Any]] = []
        self._next_id = 1
    
    def health_check(self) -> bool:
        return True
    
    def init_schema(self) -> None:
        pass
    
    def save_heatmap(
        self,
        camera_id: str,
        filename: str,
        heatmap_path: str,
        hotspot_count: int = 0,
        max_density: float = 0.0,
        avg_motion: float = 0.0,
        camera_name: str = "",
        camera_location: str = ""
    ) -> int:
        record = {
            "id": self._next_id,
            "camera_id": camera_id,
            "filename": filename,
            "heatmap_path": heatmap_path,
            "hotspot_count": hotspot_count,
            "max_density": max_density,
            "avg_motion": avg_motion,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "timestamp": datetime.now()
        }
        self._heatmaps.append(record)
        self._next_id += 1
        return record["id"]
    
    def get_heatmaps(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        results = self._heatmaps
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        if start_date:
            results = [r for r in results if r["timestamp"] >= start_date]
        if end_date:
            results = [r for r in results if r["timestamp"] <= end_date]
        return list(reversed(results[:limit]))
    
    def get_heatmap_stats(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._heatmaps
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        
        if not results:
            return {
                "total_heatmaps": 0,
                "avg_hotspots": 0.0,
                "max_density": 0.0,
                "avg_motion": 0.0
            }
        
        return {
            "total_heatmaps": len(results),
            "avg_hotspots": round(sum(r["hotspot_count"] for r in results) / len(results), 1),
            "max_density": max(r["max_density"] for r in results),
            "avg_motion": round(sum(r["avg_motion"] for r in results) / len(results), 2)
        }


class MockTrackingRepository:
    """In-memory mock of TrackingRepository."""
    
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._next_id = 1
    
    def health_check(self) -> bool:
        return True
    
    def init_schema(self) -> None:
        pass
    
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
        camera_location: str = ""
    ) -> int:
        record = {
            "id": self._next_id,
            "camera_id": camera_id,
            "filename": filename,
            "object_count": object_count,
            "trajectories": trajectories,
            "avg_speed": avg_speed,
            "max_objects": max_objects,
            "entries": entries,
            "exits": exits,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "timestamp": datetime.now()
        }
        self._events.append(record)
        self._next_id += 1
        return record["id"]
    
    def get_tracking_events(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self._events
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        return list(reversed(results[:limit]))
    
    def get_tracking_stats(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._events
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        
        if not results:
            return {
                "total_events": 0,
                "total_objects": 0,
                "avg_speed": 0.0,
                "peak_objects": 0,
                "total_entries": 0,
                "total_exits": 0
            }
        
        return {
            "total_events": len(results),
            "total_objects": sum(r["object_count"] for r in results),
            "avg_speed": round(sum(r["avg_speed"] for r in results) / len(results), 1),
            "peak_objects": max(r["max_objects"] for r in results),
            "total_entries": sum(r["entries"] for r in results),
            "total_exits": sum(r["exits"] for r in results)
        }


class MockPersonDetectionRepository:
    """In-memory mock of PersonDetectionRepository."""
    
    def __init__(self):
        self._detections: List[Dict[str, Any]] = []
        self._next_id = 1
    
    def health_check(self) -> bool:
        return True
    
    def init_schema(self) -> None:
        pass
    
    def save_person_detection(
        self,
        camera_id: str,
        filename: str,
        total_detections: int = 0,
        max_people: int = 0,
        avg_people: float = 0.0,
        detections_json: str = "",
        camera_name: str = "",
        camera_location: str = ""
    ) -> int:
        record = {
            "id": self._next_id,
            "camera_id": camera_id,
            "filename": filename,
            "total_detections": total_detections,
            "max_people": max_people,
            "avg_people": avg_people,
            "detections_json": detections_json,
            "camera_name": camera_name,
            "camera_location": camera_location,
            "timestamp": datetime.now()
        }
        self._detections.append(record)
        self._next_id += 1
        return record["id"]
    
    def get_person_detections(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self._detections
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        return list(reversed(results[:limit]))
    
    def get_person_detection_stats(self, camera_id: Optional[str] = None) -> Dict[str, Any]:
        results = self._detections
        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        
        if not results:
            return {
                "total_videos": 0,
                "total_detections": 0,
                "peak_occupancy": 0,
                "avg_people": 0.0
            }
        
        return {
            "total_videos": len(results),
            "total_detections": sum(r["total_detections"] for r in results),
            "peak_occupancy": max(r["max_people"] for r in results),
            "avg_people": round(sum(r["avg_people"] for r in results) / len(results), 1)
        }


class MockCombinedRepository(
    MockAnalyticsRepository,
    MockHeatmapRepository,
    MockTrackingRepository,
    MockPersonDetectionRepository
):
    """
    Combined mock repository implementing all interfaces.
    
    Use this when a service needs multiple repository types.
    """
    
    def __init__(self):
        # Initialize all parent classes' storage
        self._results: List[Dict[str, Any]] = []
        self._heatmaps: List[Dict[str, Any]] = []
        self._events: List[Dict[str, Any]] = []
        self._detections: List[Dict[str, Any]] = []
        self._next_id = 1
