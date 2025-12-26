from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
from typing import Optional, Any
from pathlib import Path
import logging
import os

class SystemConfig(BaseSettings):
    """
    Centralized configuration manager using Pydantic BaseSettings.
    Loads from environment variables and supports .env files.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "analytics"
    postgres_user: str = "analytics_user"
    postgres_password: SecretStr = SecretStr("analytics_pass")
    db_type: str = "postgres" 
    max_db_limit: int = 1000
    
    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    task_queue: str = "ml_processing_queue"
    queue_mode: str = "redis" # 'redis' or 'filesystem'
    
    # Storage (MinIO)
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minio_access_key"
    minio_secret_key: SecretStr = SecretStr("minio_secret_key")
    minio_bucket: str = "recordings"
    minio_secure: bool = Field(default=False)
    
    # Application
    secret_key: SecretStr = SecretStr("super-secret-key-change-it")
    log_level: str = "INFO"
    tenant_id: str = "default"
    
    # Directories
    recordings_dir: Path = Path("/app/data/vault/recordings")
    processed_dir: Path = Path("/app/data/processed")
    config_dir: Path = Path("/app/config")
    db_path: Path = Path("/app/data/analytics.db")
    
    # ML Models
    yolo_model_size: str = "yolov8n.pt"
    inference_confidence: float = 0.5
    frame_skip: int = 1
    
    # Observability
    jaeger_host: str = "jaeger"
    sentry_dsn: Optional[str] = None

    def __str__(self):
        """Custom string representation that masks secrets."""
        # This will mask all SecretStr fields automatically when converted to string
        return self.model_dump_json(indent=2)

_config: Optional[SystemConfig] = None

def get_config() -> SystemConfig:
    global _config
    if _config is None:
        try:
            _config = SystemConfig()
        except Exception as e:
            print(f"CRITICAL: Failed to load configuration: {e}")
            _config = SystemConfig.model_construct() 
    return _config
