"""
Mock Video Fixtures (Phase B3)
==============================
Standalone video fixtures.
"""

import pytest
from unittest.mock import MagicMock
import numpy as np
from pathlib import Path


@pytest.fixture
def sample_video_path(tmp_path):
    """Creates a dummy video file path."""
    video_path = tmp_path / "test_video.mp4"
    video_path.touch()
    return video_path
