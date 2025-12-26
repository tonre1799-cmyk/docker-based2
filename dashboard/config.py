"""
Dashboard Configuration
=======================
Central configuration and service initialization for the dashboard.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

# Load customer configuration
def load_customer_config():
    """Load customer configuration from YAML file."""
    config_path = Path("/app/customer_config.yaml")
    if not config_path.exists():
        config_path = PROJECT_ROOT / "customer_config.yaml"
    
    default_config = {
        "customer": {"name": "ESP32-CAM Analytics"},
        "branding": {"page_title": "Analytics Dashboard", "theme_color": "#1e3a5f"},
        "features": {"heatmaps": True, "face_recognition": False}
    }
    
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            pass
    return default_config


# Initialize services
def get_analytics_service():
    """
    Get or create the AnalyticsService singleton.
    
    Returns:
        AnalyticsService instance connected to the database
    """
    try:
        from infrastructure.repositories.postgres_repository import PostgresRepository
        from services.analytics_service import AnalyticsService
        
        repo = PostgresRepository()
        repo.init_schema()
        return AnalyticsService(
            analytics_repo=repo,
            heatmap_repo=repo,
            tracking_repo=repo,
            person_detection_repo=repo
        )
    except ImportError:
        # Fallback for when new architecture isn't fully deployed
        return None


# Configuration constants
APP_CONFIG = load_customer_config()

# Database path (for legacy compatibility)
DB_PATH = Path(os.environ.get("DB_PATH", "/app/data/analytics.db"))

# Theme settings
THEME_COLOR = APP_CONFIG.get("branding", {}).get("theme_color", "#1e3a5f")
PAGE_TITLE = APP_CONFIG.get("branding", {}).get("page_title", "Analytics Dashboard")
CUSTOMER_NAME = APP_CONFIG.get("customer", {}).get("name", "ESP32-CAM Analytics")

# Feature flags
FEATURES = APP_CONFIG.get("features", {})
ENABLE_HEATMAPS = FEATURES.get("heatmaps", True)
ENABLE_FACE_RECOGNITION = FEATURES.get("face_recognition", False)
