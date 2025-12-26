import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Camera configuration cache
_camera_config = None
_models_config = None

def load_camera_config(config_dir: Path) -> dict:
    """Load camera configuration from YAML file."""
    global _camera_config
    
    if _camera_config is not None:
        return _camera_config
    
    config_path = config_dir / "cameras.yml"
    
    if not config_path.exists():
        logger.warning(f"Camera config not found: {config_path}")
        return {"cameras": []}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f) or {"cameras": []}
            
        # Validate with Pydantic
        from core.models.camera import CameraListConfig
        validated = CameraListConfig(**raw_config)
        _camera_config = validated.model_dump()
        
        logger.info(f"Loaded {len(_camera_config.get('cameras', []))} cameras from config")
    except Exception as e:
        logger.error(f"Error loading/validating camera config: {e}")
        _camera_config = {"cameras": []}
    
    return _camera_config


def load_models_config(config_dir: Path) -> dict:
    """Load models configuration from YAML file."""
    global _models_config
    
    if _models_config is not None:
        return _models_config
    
    config_path = config_dir / "models.yml"
    
    if not config_path.exists():
        logger.warning(f"Models config not found: {config_path}")
        return {"models": []}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _models_config = yaml.safe_load(f) or {"models": []}
        logger.info(f"Loaded {len(_models_config.get('models', []))} models from config")
    except Exception as e:
        logger.error(f"Error loading models config: {e}")
        _models_config = {"models": []}
    
    return _models_config
