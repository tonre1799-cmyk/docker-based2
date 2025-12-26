"""
ML Models Package
================
Collection of ML models for video analytics.
"""

from .base_model import BaseMLModel
from .heatmap import HeatmapModel
from .tracking import ObjectTrackingModel
from .person_detection import PersonDetectionModel

__all__ = ['BaseMLModel', 'HeatmapModel', 'ObjectTrackingModel', 'PersonDetectionModel']

