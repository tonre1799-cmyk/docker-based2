"""
Global Test Fixtures
====================
Shared fixtures available to all tests.
"""

import sys
from pathlib import Path
import pytest

# Add project root to path (Removed in favor of pyproject.toml)
PROJECT_ROOT = Path(__file__).parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture
def project_root():
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def test_data_dir(project_root):
    """Return the test data directory."""
    data_dir = project_root / "tests" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_camera_id():
    """Sample camera ID for tests."""
    return "test_camera_001"


@pytest.fixture
def sample_camera_info():
    """Sample camera info dictionary."""
    return {
        "camera_id": "test_camera_001",
        "name": "Test Camera",
        "location": "Test Location",
        "ip": "192.168.1.100",
        "port": 81
    }


@pytest.fixture
def sample_analytics_result():
    """Sample analytics result dictionary."""
    return {
        "camera_id": "test_camera_001",
        "filename": "test_video.mp4",
        "visitor_count": 5,
        "motion_detected": True,
        "confidence": 0.85,
        "camera_name": "Test Camera",
        "camera_location": "Test Location"
    }


@pytest.fixture
def sample_heatmap_result():
    """Sample heatmap result dictionary."""
    return {
        "camera_id": "test_camera_001",
        "filename": "test_video.mp4",
        "heatmap_path": "/tmp/heatmap.png",
        "hotspot_count": 3,
        "max_density": 0.75,
        "avg_motion": 0.25,
        "grid_data": '{"cells": []}'
    }


@pytest.fixture
def sample_tracking_result():
    """Sample tracking result dictionary."""
    return {
        "camera_id": "test_camera_001",
        "filename": "test_video.mp4",
        "object_count": 10,
        "trajectories": '[]',
        "avg_speed": 5.5,
        "max_objects": 4,
        "entries": 6,
        "exits": 4
    }


@pytest.fixture
def sample_person_detection_result():
    """Sample person detection result dictionary."""
    return {
        "camera_id": "test_camera_001",
        "filename": "test_video.mp4",
        "total_detections": 50,
        "max_people": 8,
        "avg_people": 3.5,
        "detections_json": '[]'
    }


# =============================================================================
# Model Config Fixtures
# =============================================================================

@pytest.fixture
def heatmap_config():
    """Configuration for HeatmapModel."""
    return {
        "name": "Heatmap Model",
        "enabled": True,
        "config": {
            "grid_size": [10, 10]
        }
    }


@pytest.fixture
def tracking_config():
    """Configuration for TrackingModel."""
    return {
        "name": "Tracking Model",
        "enabled": True,
        "config": {
            "model_size": "yolov8n.pt",
            "confidence": 0.5,
            "line_position": 0.5,
            "line_orientation": "horizontal"
        }
    }


@pytest.fixture
def person_detection_config():
    """Configuration for PersonDetectionModel."""
    return {
        "name": "Person Detection Model",
        "enabled": True,
        "config": {
            "model_size": "yolov8n.pt",
            "confidence": 0.5,
            "frame_skip": 1
        }
    }
