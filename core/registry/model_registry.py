"""
Model Registry
==============
Central registry for ML model plugins.
Handles dynamic model loading, configuration, and lifecycle.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import yaml

from core.interfaces.ml_model import MLModelInterface
from core.models.model_config import ModelListConfig

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for managing ML model instances.
    
    Supports:
    - Dynamic model registration
    - Configuration-based loading
    - Model chaining setup
    - Enabled/disabled state management
    """
    
    def __init__(self):
        self._model_classes: Dict[str, Type[MLModelInterface]] = {}
        self._model_instances: Dict[str, MLModelInterface] = {}
        self._model_order: List[str] = []
        self._chain_config: Dict[str, List[str]] = {}
    
    def register_class(
        self,
        model_id: str,
        model_class: Type[MLModelInterface]
    ) -> None:
        """
        Register a model class (not instantiated yet).
        
        Args:
            model_id: Unique identifier for the model
            model_class: The model class to register
        """
        self._model_classes[model_id] = model_class
        logger.debug(f"Registered model class: {model_id}")
    
    def instantiate(
        self,
        model_id: str,
        config: Dict[str, Any]
    ) -> Optional[MLModelInterface]:
        """
        Instantiate a registered model class with configuration.
        
        Args:
            model_id: The model ID to instantiate
            config: Configuration dict for the model
            
        Returns:
            The model instance, or None if class not found
        """
        model_class = self._model_classes.get(model_id)
        if not model_class:
            logger.warning(f"Model class not found: {model_id}")
            return None
        
        try:
            instance = model_class(config)
            self._model_instances[model_id] = instance
            if model_id not in self._model_order:
                self._model_order.append(model_id)
            logger.info(f"Instantiated model: {model_id}")
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate model {model_id}: {e}")
            return None
    
    def get(self, model_id: str) -> Optional[MLModelInterface]:
        """Get a model instance by ID."""
        return self._model_instances.get(model_id)
    
    def get_enabled(self) -> List[MLModelInterface]:
        """Get all enabled model instances in execution order."""
        return [
            self._model_instances[model_id]
            for model_id in self._model_order
            if model_id in self._model_instances
            and self._model_instances[model_id].enabled
        ]
    
    def get_all(self) -> List[MLModelInterface]:
        """Get all model instances in execution order."""
        return [
            self._model_instances[model_id]
            for model_id in self._model_order
            if model_id in self._model_instances
        ]
    
    def set_chain(self, target_model: str, source_models: List[str]) -> None:
        """
        Configure model chaining - which models feed into which.
        
        Args:
            target_model: Model that receives chained input
            source_models: Models that provide input to target
        """
        self._chain_config[target_model] = source_models
    
    def get_chain_sources(self, model_id: str) -> List[str]:
        """Get the source models for a given target model."""
        return self._chain_config.get(model_id, [])
    
    def load_from_config(self, config_path: Path) -> None:
        """
        Load model configurations from a YAML file.
        
        Expected format:
        ```yaml
        models:
          - id: "model_id"
            name: "Model Name"
            enabled: true
            config:
              key: value
        ```
        """
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return
        
        try:
            with open(config_path, 'r') as f:
                raw_data = yaml.safe_load(f) or {"models": []}
            
            # Validate with Pydantic
            validated_config = ModelListConfig(**raw_data)
            
            for model_cfg in validated_config.models:
                model_id = model_cfg.id
                
                if model_id in self._model_classes:
                    # Convert Pydantic model back to dict for the model constructor
                    # (MLWorker models expect a dict for now)
                    instance = self.instantiate(model_id, model_cfg.model_dump())
                    
                    # Set dependencies
                    if instance and model_cfg.dependencies:
                        self.set_chain(model_id, model_cfg.dependencies)
                        logger.debug(f"Set dependencies for {model_id}: {model_cfg.dependencies}")
                else:
                    logger.debug(f"Model class not registered: {model_id}")
            
            # Setup default chains only for models that don't have explicit dependencies
            self._setup_default_chains()
            
            logger.info(f"Loaded {len(self._model_instances)} models from config")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def _setup_default_chains(self) -> None:
        """Setup default model chaining based on known dependencies (if not explicitly set)."""
        # Heatmap can use person detection or tracking results
        if 'heatmap' in self._model_instances and 'heatmap' not in self._chain_config:
            sources = []
            if 'person_detection' in self._model_instances:
                sources.append('person_detection')
            elif 'tracking' in self._model_instances:
                sources.append('tracking')
            if sources:
                self.set_chain('heatmap', sources)
    
    def unregister(self, model_id: str) -> None:
        """Remove a model from the registry."""
        self._model_instances.pop(model_id, None)
        self._model_classes.pop(model_id, None)
        if model_id in self._model_order:
            self._model_order.remove(model_id)
    
    def clear(self) -> None:
        """Clear all registered models."""
        self._model_instances.clear()
        self._model_classes.clear()
        self._model_order.clear()
        self._chain_config.clear()
    
    def __len__(self) -> int:
        return len(self._model_instances)
    
    def __contains__(self, model_id: str) -> bool:
        return model_id in self._model_instances
