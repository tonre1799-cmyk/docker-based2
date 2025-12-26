"""
Repository Implementations Package
=================================
Provides factory functions to instantiate repositories based on configuration.
"""

import os
import logging
from pathlib import Path

from .postgres_repository import PostgresRepository
from .sqlite_repository import SqliteRepository

logger = logging.getLogger(__name__)

def get_repository(repo_type: str = None):
    """
    Factory function to get the appropriate repository implementation.
    
    Args:
        repo_type: Type of repository ('postgres' or 'sqlite'). 
                  If None, read from DB_TYPE environment variable.
                  
    Returns:
        A repository instance implementing all necessary interfaces.
    """
    from core.config_manager import get_config
    config = get_config()
    
    db_type = repo_type or config.db_type.lower()
    
    if db_type == 'postgres':
        logger.info("Initializing PostgresRepository")
        return PostgresRepository(
            host=config.postgres_host,
            port=config.postgres_port,
            database=config.postgres_db,
            user=config.postgres_user,
            password=config.postgres_password.get_secret_value() if hasattr(config.postgres_password, 'get_secret_value') else config.postgres_password
        )
    else:
        raise ValueError(f"Unsupported or disabled database type: {db_type}. This system now requires PostgreSQL.")

__all__ = ['PostgresRepository', 'get_repository']
