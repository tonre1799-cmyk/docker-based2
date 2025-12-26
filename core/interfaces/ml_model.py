"""
ML Model Interface
==================
Protocol/interface for all ML models in the system.
Models must implement this interface to be registered with ModelRegistry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.results import BaseResult


@dataclass
class ProcessingContext:
    """
    Context passed to ML models during processing.
    Contains metadata about the video and camera.
    """
    camera_id: str
    camera_name: str = ""
    camera_location: str = ""
    filename: str = ""
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # For model chaining - previous model results
    previous_results: Dict[str, Any] = field(default_factory=dict)


class MLModelInterface(ABC):
    """
    Abstract base class for all ML models.
    
    All models must implement:
    - process_video(): Run inference on a video file
    - get_model_id(): Return unique model identifier
    - get_result_type(): Return the result dataclass type
    """
    
    @property
    @abstractmethod
    def model_id(self) -> str:
        """Unique identifier for this model."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this model."""
        pass
    
    @property
    def enabled(self) -> bool:
        """Whether this model is enabled."""
        return True
    
    @abstractmethod
    def process_video(
        self,
        video_path: Path,
        context: ProcessingContext
    ) -> Dict[str, Any]:
        """
        Process a video file and return results.
        
        Args:
            video_path: Path to the video file
            context: Processing context with camera info and config
            
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
    
    def get_config(self) -> Dict[str, Any]:
        """Return current model configuration."""
        return getattr(self, 'config', {})
    
    def accepts_chained_input(self) -> bool:
        """
        Whether this model can accept input from previous models.
        Override to True for models like Heatmap that use detection data.
        """
        return False
    
    def set_chained_input(self, model_id: str, results: Dict[str, Any]) -> None:
        """
        Receive results from a previous model in the chain.
        Override in models that use chained input.
        """
        pass
    
    def __str__(self) -> str:
        return f"{self.name} ({self.model_id})"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.model_id}>"
