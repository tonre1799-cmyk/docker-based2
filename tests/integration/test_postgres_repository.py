"""
Integration Tests for PostgresRepository
========================================
Test real database interactions.
Requires a running PostgreSQL instance.
Skipped if connection details are not provided.
"""

import pytest
import os
import psycopg2
from infrastructure.repositories.postgres_repository import PostgresRepository

# Get DB config from env or use defaults for local test
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_NAME = os.getenv("POSTGRES_DB", "kerberos_ml_test")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

def is_db_available():
    """Check if DB is reachable."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=1
        )
        conn.close()
        return True
    except Exception:
        return False

@pytest.mark.integration
@pytest.mark.skipif(not is_db_available(), reason="Database not available")
class TestPostgresRepository:
    """Integration tests for PostgresRepository."""
    
    @pytest.fixture
    def isolated_db(self):
        """Create a unique test database for isolation."""
        import uuid
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to system DB to create test DB
        sys_conn = psycopg2.connect(
            host=DB_HOST, database='postgres', user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        sys_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        sys_cursor = sys_conn.cursor()
        
        test_db_name = f"test_db_{uuid.uuid4().hex}"
        # Validate name (should only contain alphanumeric and underscores)
        if not all(c.isalnum() or c in "_" for c in test_db_name):
            raise ValueError(f"Invalid database name: {test_db_name}")
            
        sys_cursor.execute(f"CREATE DATABASE {test_db_name}")
        sys_cursor.close()
        sys_conn.close()
        
        yield {
            'host': DB_HOST,
            'database': test_db_name,
            'user': DB_USER,
            'password': DB_PASS,
            'port': int(DB_PORT)
        }
        
        # Cleanup
        sys_conn = psycopg2.connect(
            host=DB_HOST, database='postgres', user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        sys_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        sys_cursor = sys_conn.cursor()
        
        # Safe after validation above
        sys_cursor.execute(f"DROP DATABASE IF EXISTS {test_db_name}")
        sys_cursor.close()
        sys_conn.close()

    @pytest.fixture
    def repo(self, isolated_db):
        """Create repository instance with isolated DB."""
        repo = PostgresRepository(
            host=isolated_db['host'],
            database=isolated_db['database'], 
            user=isolated_db['user'],
            password=isolated_db['password'],
            port=isolated_db['port']
        )
        repo.init_schema()
        return repo

    def test_save_and_get_analytics(self, repo):
        """Can save and retrieve analytics results in real DB."""
        idx = repo.save_result(
            "cam1", "vid1.mp4", 5, True, 0.95, 
            "Front Door", "Entrance"
        )
        assert idx is not None
        
        results = repo.get_results(camera_id="cam1")
        assert len(results) == 1
        assert results[0]["visitor_count"] == 5
        assert results[0]["camera_name"] == "Front Door"

    def test_get_stats_aggregation(self, repo):
        """Real SQL aggregation works."""
        repo.save_result("cam1", "v1", 10, True, 1.0)
        repo.save_result("cam1", "v2", 20, False, 0.5)
        
        stats = repo.get_stats("cam1")
        assert stats["total_visitors"] == 30
        # Check float math from DB matches
        assert 0.74 < stats["avg_confidence"] < 0.76

    def test_save_and_get_heatmaps(self, repo):
        """Can save and retrieve heatmaps."""
        repo.save_heatmap(
            "cam1", "v1", "path/to/img.png", 
            10, 0.8, 0.5
        )
        
        results = repo.get_heatmaps("cam1")
        assert len(results) == 1
        assert results[0]["heatmap_path"] == "path/to/img.png"
