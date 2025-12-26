from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ModelConfig(BaseModel):
    """Configuration for a single ML model."""
    id: str = Field(..., description="Unique identifier for the model (e.g., 'heatmap')")
    name: str = Field(..., description="Human-readable name")
    enabled: bool = Field(True, description="Whether the model is active")
    config: Dict[str, Any] = Field(default_factory=dict, description="Model-specific parameters")
    dependencies: List[str] = Field(default_factory=list, description="IDs of models that must run before this one")

class ModelListConfig(BaseModel):
    """Root configuration for the models.yml file."""
    models: List[ModelConfig]
