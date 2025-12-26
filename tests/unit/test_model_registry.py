"""
Test Model Registry (Phase A2/C1)
=================================
Test ModelRegistry: registration, lookup, chaining.
"""

import pytest
from pathlib import Path
from typing import Dict, Any


class MockMLModel:
    """Simple mock ML model for testing registry."""
    
    def __init__(self, model_id: str, config: dict):
        self._model_id = model_id
        self._name = config.get('name', model_id)
        self._enabled = config.get('enabled', True)
        self.config = config.get('config', {})
    
    @property
    def model_id(self) -> str:
        return self._model_id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    def process_video(self, video_path: Path, context=None) -> Dict[str, Any]:
        return {"mock": True, "model_id": self.model_id}
    
    def get_result_type(self) -> str:
        return "mock"
    
    def accepts_chained_input(self) -> bool:
        return False


class TestModelRegistry:
    """Test ModelRegistry class."""
    
    def test_register_and_get(self):
        """Can register a model class and instantiate it."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("mock_model", MockMLModel)
        
        instance = registry.instantiate("mock_model", {
            "name": "Test Model",
            "enabled": True
        })
        
        assert instance is not None
        assert instance.model_id == "mock_model"
        assert instance.name == "Test Model"
    
    def test_get_returns_instance(self):
        """get() returns the instantiated model."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("mock_model", MockMLModel)
        registry.instantiate("mock_model", {"name": "Test"})
        
        model = registry.get("mock_model")
        assert model is not None
        assert model.model_id == "mock_model"
    
    def test_get_nonexistent_returns_none(self):
        """get() returns None for unregistered model."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        
        model = registry.get("nonexistent")
        assert model is None
    
    def test_get_enabled_filters_disabled(self):
        """get_enabled() only returns enabled models."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("model1", MockMLModel)
        registry.register_class("model2", MockMLModel)
        
        registry.instantiate("model1", {"name": "Model 1", "enabled": True})
        registry.instantiate("model2", {"name": "Model 2", "enabled": False})
        
        enabled = registry.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].model_id == "model1"
    
    def test_get_all_returns_all(self):
        """get_all() returns all models regardless of enabled state."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("model1", MockMLModel)
        registry.register_class("model2", MockMLModel)
        
        registry.instantiate("model1", {"enabled": True})
        registry.instantiate("model2", {"enabled": False})
        
        all_models = registry.get_all()
        assert len(all_models) == 2
    
    def test_set_chain(self):
        """Can set up model chaining."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.set_chain("heatmap", ["person_detection"])
        
        sources = registry.get_chain_sources("heatmap")
        assert sources == ["person_detection"]
    
    def test_chain_sources_empty_if_not_set(self):
        """get_chain_sources() returns empty list if not configured."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        
        sources = registry.get_chain_sources("unknown_model")
        assert sources == []
    
    def test_unregister(self):
        """Can unregister a model."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("model1", MockMLModel)
        registry.instantiate("model1", {})
        
        assert "model1" in registry
        
        registry.unregister("model1")
        
        assert "model1" not in registry
    
    def test_clear(self):
        """Can clear all models."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("model1", MockMLModel)
        registry.register_class("model2", MockMLModel)
        registry.instantiate("model1", {})
        registry.instantiate("model2", {})
        
        assert len(registry) == 2
        
        registry.clear()
        
        assert len(registry) == 0
    
    def test_len(self):
        """len() returns number of instantiated models."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        assert len(registry) == 0
        
        registry.register_class("model1", MockMLModel)
        registry.instantiate("model1", {})
        
        assert len(registry) == 1
    
    def test_contains(self):
        """'in' operator works for checking model existence."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("model1", MockMLModel)
        registry.instantiate("model1", {})
        
        assert "model1" in registry
        assert "nonexistent" not in registry
    
    def test_instantiate_nonexistent_class_returns_none(self):
        """instantiate() returns None for unregistered class."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        
        result = registry.instantiate("nonexistent", {})
        assert result is None
    
    def test_execution_order_preserved(self):
        """Models are returned in registration order."""
        from core.registry.model_registry import ModelRegistry
        
        registry = ModelRegistry()
        registry.register_class("first", MockMLModel)
        registry.register_class("second", MockMLModel)
        registry.register_class("third", MockMLModel)
        
        registry.instantiate("first", {"enabled": True})
        registry.instantiate("second", {"enabled": True})
        registry.instantiate("third", {"enabled": True})
        
        models = registry.get_enabled()
        assert [m.model_id for m in models] == ["first", "second", "third"]
