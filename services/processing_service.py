"""
Processing Service
==================
Orchestrates ML video processing pipeline.
Handles model execution, chaining, and result persistence.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.interfaces.ml_model import MLModelInterface, ProcessingContext
from core.interfaces.repository import (
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository
)
from core.registry.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a video through the ML pipeline."""
    camera_id: str
    filename: str
    success: bool = True
    model_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0


@dataclass
class CameraInfo:
    """Camera metadata for processing context."""
    camera_id: str
    name: str = ""
    location: str = ""
    config_overrides: Dict[str, Any] = field(default_factory=dict)


class ProcessingService:
    """
    Service layer for ML video processing.
    
    Responsibilities:
    - Orchestrate model execution in correct order
    - Handle model output chaining
    - Persist results via repositories
    - Handle errors gracefully
    """
    
    def __init__(
        self,
        registry: ModelRegistry,
        analytics_repo: AnalyticsRepository = None,
        heatmap_repo: HeatmapRepository = None,
        tracking_repo: TrackingRepository = None,
        person_detection_repo: PersonDetectionRepository = None
    ):
        """
        Initialize processing service.
        
        Args:
            registry: ModelRegistry with registered models
            *_repo: Repository implementations for persisting results
        """
        self.registry = registry
        self.analytics_repo = analytics_repo
        self.heatmap_repo = heatmap_repo
        self.tracking_repo = tracking_repo
        self.person_detection_repo = person_detection_repo
    
    def process_video(
        self,
        video_path: Path,
        camera_info: CameraInfo,
        tenant_id: str = "default"
    ) -> ProcessingResult:
        """
        Process a video file through all enabled ML models.
        
        Args:
            video_path: Path to the video file
            camera_info: Camera metadata
            tenant_id: Tenant context
            
        Returns:
            ProcessingResult with all model outputs
        """
        import time
        start_time = time.time()
        
        result = ProcessingResult(
            camera_id=camera_info.camera_id,
            filename=video_path.name
        )
        
        # Get enabled models in execution order
        models = self.registry.get_enabled()
        
        if not models:
            result.errors.append("No enabled models found")
            result.success = False
            return result
        
        logger.info(f"Processing {video_path.name} with {len(models)} models for tenant {tenant_id}")
        
        # Create processing context
        context = ProcessingContext(
            camera_id=camera_info.camera_id,
            camera_name=camera_info.name,
            camera_location=camera_info.location,
            filename=video_path.name,
            config_overrides=camera_info.config_overrides,
            tenant_id=tenant_id
        )
        
        # Store results for chaining
        all_results: Dict[str, Dict[str, Any]] = {}
        
        # Process each model
        for model in models:
            try:
                # Check for model chaining
                if model.accepts_chained_input():
                    sources = self.registry.get_chain_sources(model.model_id)
                    for source_id in sources:
                        if source_id in all_results:
                            model.set_chained_input(source_id, all_results[source_id])
                
                # Update context with previous results
                context.previous_results = all_results.copy()
                
                # Run model
                logger.info(f"Running model: {model.name}")
                model_result = model.process_video(video_path, context)
                
                # Store results
                all_results[model.model_id] = model_result
                result.model_results[model.model_id] = model_result
                
                # Persist results
                self._persist_result(
                    model=model,
                    model_result=model_result,
                    camera_info=camera_info,
                    filename=video_path.name,
                    tenant_id=tenant_id
                )
                
                logger.info(f"Model {model.name} completed successfully")
                
            except Exception as e:
                error_msg = f"Error in model {model.model_id}: {str(e)}"
                logger.error(error_msg)
                result.errors.append(error_msg)
        
        # Calculate processing time
        result.processing_time_ms = (time.time() - start_time) * 1000
        result.success = len(result.errors) == 0
        
        logger.info(
            f"Processing complete: {result.camera_id}/{result.filename} "
            f"in {result.processing_time_ms:.0f}ms "
            f"({len(result.model_results)} models, {len(result.errors)} errors)"
        )
        
        return result
    
    def _persist_result(
        self,
        model: MLModelInterface,
        model_result: Dict[str, Any],
        camera_info: CameraInfo,
        filename: str,
        tenant_id: str = "default"
    ) -> Optional[int]:
        """
        Persist model result to appropriate repository.
        
        Args:
            model: The model that produced the result
            model_result: The result data
            camera_info: Camera metadata
            filename: Video filename
            tenant_id: Tenant context
            
        Returns:
            Record ID if persisted, None otherwise
        """
        result_type = model.get_result_type()
        
        try:
            if result_type == 'analytics' and self.analytics_repo:
                return self.analytics_repo.save_result(
                    camera_id=camera_info.camera_id,
                    filename=filename,
                    visitor_count=model_result.get('visitor_count', 0),
                    motion_detected=model_result.get('motion_detected', False),
                    confidence=model_result.get('confidence', 0.0),
                    camera_name=camera_info.name,
                    camera_location=camera_info.location,
                    tenant_id=tenant_id
                )
            
            elif result_type == 'heatmap' and self.heatmap_repo:
                return self.heatmap_repo.save_heatmap(
                    camera_id=camera_info.camera_id,
                    filename=filename,
                    heatmap_path=model_result.get('heatmap_path', ''),
                    hotspot_count=model_result.get('hotspot_count', 0),
                    max_density=model_result.get('max_density', 0.0),
                    avg_motion=model_result.get('avg_motion', 0.0),
                    camera_name=camera_info.name,
                    camera_location=camera_info.location,
                    tenant_id=tenant_id
                )
            
            elif result_type == 'tracking' and self.tracking_repo:
                return self.tracking_repo.save_tracking_event(
                    camera_id=camera_info.camera_id,
                    filename=filename,
                    object_count=model_result.get('object_count', 0),
                    trajectories=model_result.get('trajectories', ''),
                    avg_speed=model_result.get('avg_speed', 0.0),
                    max_objects=model_result.get('max_objects', 0),
                    entries=model_result.get('entries', 0),
                    exits=model_result.get('exits', 0),
                    camera_name=camera_info.name,
                    camera_location=camera_info.location,
                    tenant_id=tenant_id
                )
            
            elif result_type == 'person_detection' and self.person_detection_repo:
                return self.person_detection_repo.save_person_detection(
                    camera_id=camera_info.camera_id,
                    filename=filename,
                    total_detections=model_result.get('total_detections', 0),
                    max_people=model_result.get('max_people', 0),
                    avg_people=model_result.get('avg_people', 0.0),
                    detections_json=model_result.get('detections_json', ''),
                    camera_name=camera_info.name,
                    camera_location=camera_info.location,
                    tenant_id=tenant_id
                )
            
            else:
                logger.warning(f"No repository for result type: {result_type} for tenant {tenant_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to persist {result_type} result for tenant {tenant_id}: {e}")
            return None
    
    def get_registered_models(self) -> List[Dict[str, Any]]:
        """Get info about all registered models."""
        return [
            {
                "id": model.model_id,
                "name": model.name,
                "enabled": model.enabled,
                "result_type": model.get_result_type(),
                "accepts_chained_input": model.accepts_chained_input()
            }
            for model in self.registry.get_all()
        ]
