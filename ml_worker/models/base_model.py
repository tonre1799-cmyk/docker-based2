"""
Base ML Model
=============
Abstract base class for all ML models.
Updated to implement the new MLModelInterface while maintaining backward compatibility.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import sys

# Add project root to path for core imports (Removed in favor of pyproject.toml)
# PROJECT_ROOT = Path(__file__).parent.parent.parent
# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.interfaces.ml_model import MLModelInterface, ProcessingContext
    HAS_CORE = True
except ImportError:
    HAS_CORE = False
    # Fallback ProcessingContext for backward compatibility
    class ProcessingContext:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)


class BaseMLModel(ABC):
    """
    Base class for all ML models.
    
    Implements MLModelInterface and provides backward compatibility
    with existing model implementations.
    """
    
    def __init__(self, model_id: str, config: dict):
        """
        Initialize the model.
        
        Args:
            model_id: Unique model identifier
            config: Model configuration dict (from models.yml)
        """
        self._model_id = model_id
        self._name = config.get('name', model_id)
        self.config = config.get('config', {})
        self._version = config.get('version', '1.0.0')
        self._enabled = config.get('enabled', True)
        self._shared_detections = None  # For model chaining
    
    @property
    def model_id(self) -> str:
        """Unique identifier for this model."""
        return self._model_id
    
    @model_id.setter
    def model_id(self, value: str):
        self._model_id = value
    
    @property
    def name(self) -> str:
        """Human-readable name for this model."""
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value
    
    @property
    def version(self) -> str:
        """Model semantic version."""
        return self._version

    @version.setter
    def version(self, value: str):
        self._version = value
    
    @property
    def enabled(self) -> bool:
        """Whether this model is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    @abstractmethod
    def process_video(self, video_path: Path, context: ProcessingContext = None) -> Dict[str, Any]:
        """
        Process a video file and return results.
        
        Args:
            video_path: Path to the video file
            context: Optional processing context with camera info
            
        Returns:
            Dictionary with model-specific results
        """
        pass
    
    @abstractmethod
    def get_result_type(self) -> str:
        """
        Return the result type identifier.
        Used to determine which repository to use for saving.
        
        Returns one of: 'analytics', 'heatmap', 'tracking', 'person_detection'
        """
        pass
    
    def save_results(
        self,
        db_path: Path,
        camera_id: str,
        camera_info: dict,
        filename: str,
        results: dict,
        tenant_id: str = "default"
    ) -> int:
        """
        Save results to the database.
        
        DEPRECATED: Results are now saved via ProcessingService.
        Kept for backward compatibility.
        
        Args:
            db_path: Path to database (ignored in new architecture)
            camera_id: Camera identifier
            camera_info: Camera metadata
            filename: Video filename
            results: Processing results from process_video()
            
        Returns:
            Database row ID or 0 if not implemented
        """
        # Subclasses can override this for backward compatibility
        return 0
    
    def accepts_chained_input(self) -> bool:
        """
        Whether this model can accept input from previous models.
        Override to True for models like Heatmap that use detection data.
        """
        return False
    
    def set_chained_input(self, model_id: str, results: Dict[str, Any]) -> None:
        """
        Receive results from a previous model in the chain.
        
        Args:
            model_id: ID of the source model
            results: Results from the source model
        """
        # Default: store in _shared_detections for models that use it
        if 'detections' in results:
            self._shared_detections = results.get('detections', [])
    
    def get_config(self) -> Dict[str, Any]:
        """Return current model configuration."""
        return self.config
    
    def __str__(self):
        return f"{self.name} ({self.model_id})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.model_id}>"

