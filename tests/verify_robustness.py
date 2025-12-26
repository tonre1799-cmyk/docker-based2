import os
import pytest
from core.config_validator import SystemConfig, ConfigurationError
from ml_worker.database import get_connection_with_retry
from unittest.mock import patch, MagicMock
import psycopg2
import sqlite3

def test_config_validation_fails_fast():
    """Verify that SystemConfig fails when required env vars are missing."""
    with patch.dict(os.environ, {}, clear=True):
        # Even with empty env, it might use internal defaults
        # But we removed MINIO_ACCESS_KEY from defaults
        with pytest.raises(ConfigurationError, match="Missing required env vars: MINIO_ACCESS_KEY, MINIO_SECRET_KEY"):
            SystemConfig.from_env()

def test_config_invalid_port():
    """Verify that invalid port range raises error."""
    with patch.dict(os.environ, {"POSTGRES_PORT": "70000", "MINIO_ACCESS_KEY": "test", "MINIO_SECRET_KEY": "test"}):
        with pytest.raises(ConfigurationError, match="Invalid port range"):
            SystemConfig.from_env()

@patch('psycopg2.connect')
@patch('ml_worker.database.DB_TYPE', 'postgres')
def test_database_retry_logic(mock_connect):
    """Verify database retry logic with exponential backoff."""
    # Mock connection to fail 3 times then succeed
    mock_connect.side_effect = [
        psycopg2.OperationalError("Connection refused"),
        psycopg2.OperationalError("Connection refused"),
        psycopg2.OperationalError("Connection refused"),
        MagicMock() # Success
    ]
    
    # We need to mock cursor and execute for the success case
    mock_conn = mock_connect.return_value
    mock_cursor = mock_conn.cursor.return_value
    
    with patch('time.sleep') as mock_sleep:
        conn = get_connection_with_retry(max_retries=5, delay=0.1)
        assert conn is not None
        assert mock_connect.call_count == 4
        assert mock_sleep.call_count == 3

if __name__ == "__main__":
    # Manually run simple checks if pytest not available or for quick feedback
    try:
        test_config_validation_fails_fast()
        print("✓ Config validation fail-fast passed")
    except Exception as e:
        print(f"✗ Config validation fail-fast failed: {e}")

    try:
        test_config_invalid_port()
        print("✓ Config invalid port check passed")
    except Exception as e:
        print(f"✗ Config invalid port check failed: {e}")
