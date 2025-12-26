"""
Central Configuration Facade
============================
Bridges legacy code to the new SystemConfig in core/config_manager.
Maintained for backward compatibility.
"""

from core.config_manager import get_config

# Initialize configuration
_config = get_config()

class DatabaseConfig:
    HOST = _config.postgres_host
    PORT = _config.postgres_port
    NAME = _config.postgres_db
    USER = _config.postgres_user
    PASSWORD = _config.postgres_password
    DB_PATH = _config.db_path
    TYPE = _config.db_type

class InfrastructureConfig:
    # Paths
    RECORDINGS_DIR = _config.recordings_dir
    PROCESSED_DIR = _config.processed_dir
    CONFIG_DIR = _config.config_dir

    # MinIO
    MINIO_ENDPOINT = _config.minio_endpoint
    MINIO_ACCESS_KEY = _config.minio_access_key
    MINIO_SECRET_KEY = _config.minio_secret_key
    MINIO_BUCKET = _config.minio_bucket

class RedisConfig:
    HOST = _config.redis_host
    PORT = _config.redis_port
    TASK_QUEUE = _config.task_queue
    MODE = _config.queue_mode

class MLConfig:
    CONFIDENCE = _config.inference_confidence
    FRAME_SKIP = _config.frame_skip
    YOLO_MODEL = _config.yolo_model_size
