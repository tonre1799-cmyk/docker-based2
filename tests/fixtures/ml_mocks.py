"""
Mock ML Fixtures (Phase B2/B3)
==============================
Fakes for VideoCapture, CV2, and YOLO models.
"""

import pytest
from unittest.mock import MagicMock
import numpy as np


@pytest.fixture
def mock_video_capture():
    """
    Creates a mock cv2.VideoCapture object.
    
    Usage:
        def test_video(mock_video_capture):
            with patch('cv2.VideoCapture', return_value=mock_video_capture):
                process_video()
    """
    cap = MagicMock()
    
    # Setup standard properties
    cap.isOpened.return_value = True
    cap.get.side_effect = lambda prop: {
        3: 1920, # CAP_PROP_FRAME_WIDTH
        4: 1080, # CAP_PROP_FRAME_HEIGHT
        7: 30    # CAP_PROP_FRAME_COUNT
    }.get(prop, 0)
    
    # Create a fake black frame
    fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
    
    # Return 30 frames then stop
    cap.read.side_effect = ([(True, fake_frame)] * 30) + [(False, None)]
    
    return cap


@pytest.fixture
def mock_yolo_model():
    """
    Creates a mock YOLO model.
    """
    model = MagicMock()
    
    # Mock detection result
    mock_result = MagicMock()
    # Fake boxes: [x, y, w, h] normalized or pixels depending on usage
    mock_result.boxes.xywhn.tolist.return_value = [[0.5, 0.5, 0.1, 0.2]]
    mock_result.boxes.cls.tolist.return_value = [0] # Class 0 = person
    mock_result.boxes.conf.tolist.return_value = [0.9]
    mock_result.names = {0: 'person'}
    
    # Return list of results (one per frame)
    model.return_value = [mock_result]
    
    # Enable chaining calls like model.track()
    model.track.return_value = [mock_result]
    
    return model
