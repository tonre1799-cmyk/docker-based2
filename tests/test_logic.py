import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Add ml_worker to path to import modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "ml_worker"))

from models.heatmap import HeatmapModel

@pytest.fixture
def config():
    return {'grid_size': [10, 10]}

@pytest.fixture
def heatmap_model(config):
    # Mocking BaseMLModel __init__ if it does heavy lifting, 
    # but usually it just sets config. 
    # We might need to mock SonyHeatmapAdapter if it requires libs
    with patch("models.heatmap.SonyHeatmapAdapter") as MockAdapter:
        model = HeatmapModel(config)
        yield model

def test_initialization(heatmap_model):
    """Test that the model initializes correctly."""
    assert heatmap_model.name == "heatmap"
    assert heatmap_model.config['grid_size'] == [10, 10]
    assert heatmap_model._shared_detections == None

def test_set_person_detections(heatmap_model):
    """Test processing logic receiving detections."""
    detections = {'detections': [{'humans': [{'x': 50, 'y': 50}]}]}
    heatmap_model.set_person_detections(detections)
    assert len(heatmap_model._shared_detections) == 1
    assert heatmap_model._shared_detections[0]['humans'][0]['x'] == 50

@patch("models.heatmap.cv2.VideoCapture")
def test_process_from_detections(mock_cap, heatmap_model):
    """Test generating heatmap from shared detections."""
    # Setup mock video capture
    mock_cap.return_value.isOpened.return_value = True
    mock_cap.return_value.get.side_effect = [1920, 1080] # width, height
    mock_cap.return_value.read.return_value = (True, "fake_frame")
    
    # Setup model state
    detections = [{'humans': [{'x': 100, 'y': 100}, {'x': 200, 'y': 200}]}]
    heatmap_model._shared_detections = detections
    
    # Mock adapter response
    heatmap_model.adapter.generate_from_detections.return_value = {
        'heatmap_image': "fake_image",
        'hotspot_count': 2,
        'max_density': 0.8,
        'avg_density': 0.1,
        'grid_data': {}
    }
    
    # Mock file operations to avoid disk I/O
    with patch("models.heatmap.cv2.imwrite") as mock_write, \
         patch("pathlib.Path.mkdir"):
        
        result = heatmap_model.process_video(Path("test_video.mp4"))
        
        # Verify
        assert result['hotspot_count'] == 2
        assert result['max_density'] == 0.8
        mock_write.assert_called_once()
        
        # Verify adapter was called with correct points
        expected_points = [{'x': 100, 'y': 100}, {'x': 200, 'y': 200}]
        args = heatmap_model.adapter.generate_from_detections.call_args
        assert args[0][0] == expected_points

