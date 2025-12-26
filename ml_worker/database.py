"""
Database Abstraction Layer
===========================
Supports both SQLite (for single-instance/dev) and PostgreSQL (for production/scale).
Set DB_TYPE environment variable to 'postgres' or 'sqlite' (default: sqlite).
"""

import os
import sqlite3
import psycopg2
import psycopg2.extras
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from psycopg2 import pool

# Load configuration
from core.config_manager import get_config
config = get_config()

DB_TYPE = config.db_type.lower()
DB_PATH = config.db_path

PG_HOST = config.postgres_host
PG_PORT = config.postgres_port
PG_DATABASE = config.postgres_db
PG_USER = config.postgres_user
PG_PASSWORD = config.postgres_password

# Max results limit to prevent OOM
MAX_LIMIT = int(os.environ.get("MAX_DB_LIMIT", 1000))

# Connection Pool for Postgres
_pg_pool = None

def get_pool():
    """Get or initialize connection pool."""
    global _pg_pool
    if DB_TYPE == "postgres" and _pg_pool is None:
        try:
            _pg_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DATABASE,
                user=PG_USER,
                password=PG_PASSWORD.get_secret_value() if hasattr(PG_PASSWORD, 'get_secret_value') else PG_PASSWORD
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create connection pool: {e}")
            raise
    return _pg_pool


def get_connection_with_retry(max_retries=5, delay=2):
    """Get database connection with exponential backoff."""
    for attempt in range(max_retries):
        try:
            if DB_TYPE == "postgres":
                pool = get_pool()
                conn = pool.getconn()
            else:
                conn = sqlite3.connect(str(DB_PATH))
                conn.row_factory = sqlite3.Row
            
            # Test connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return conn
            
        except (psycopg2.OperationalError, sqlite3.OperationalError) as e:
            if attempt == max_retries - 1:
                import logging
                logging.getLogger(__name__).error(f"Database connection failed after {max_retries} attempts.")
                raise
            
            import time
            import logging
            wait_time = delay * (2 ** attempt)
            logging.getLogger(__name__).warning(
                f"Database connection failed (attempt {attempt+1}/{max_retries}): {e}. "
                f"Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)


@contextmanager
def get_connection():
    """Get database connection with retry logic and pool handling."""
    conn = None
    try:
        conn = get_connection_with_retry()
        yield conn
    finally:
        if conn:
            if DB_TYPE == "postgres" and _pg_pool:
                _pg_pool.putconn(conn)
            else:
                conn.close()


@contextmanager
def transaction():
    """Context manager for database transactions."""
    with get_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def is_processed(filename: str, tenant_id: str = "default") -> bool:
    """Check if a file has already been processed for a tenant."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if DB_TYPE == "postgres":
            cursor.execute("SELECT 1 FROM processed_files WHERE filename = %s AND tenant_id = %s", (filename, tenant_id))
        else:
            cursor.execute("SELECT 1 FROM processed_files WHERE filename = ? AND tenant_id = ?", (filename, tenant_id))
        return cursor.fetchone() is not None


def mark_processed(filename: str, camera_id: str = None, tenant_id: str = "default", metadata_json: str = None) -> bool:
    """
    Mark a file as processed for a tenant. 
    Returns True if the file was newly marked as processed.
    Returns False if the file was already processed.
    """
    with transaction() as conn:
        cursor = conn.cursor()
        if DB_TYPE == "postgres":
            cursor.execute("""
                INSERT INTO processed_files (filename, camera_id, tenant_id, metadata_json, processed_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (filename, tenant_id) DO NOTHING
            """, (filename, camera_id, tenant_id, metadata_json))
            return cursor.rowcount > 0
        else:
            # SQLite: Check existence first to be safe, then insert
            cursor.execute("SELECT 1 FROM processed_files WHERE filename = ? AND tenant_id = ?", (filename, tenant_id))
            if cursor.fetchone():
                return False
                
            cursor.execute("""
                INSERT INTO processed_files (filename, camera_id, tenant_id, metadata_json)
                VALUES (?, ?, ?, ?)
            """, (filename, camera_id, tenant_id, metadata_json))
            return True


def init_db(db_path: Path = None) -> None:
    """Initialize the database with required tables."""
    if DB_TYPE == "postgres":
        import logging
        logging.getLogger(__name__).info("PostgreSQL schema initialization deferred to Alembic migrations.")
        return
        
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Analytics table
        if DB_TYPE == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    visitor_count INTEGER DEFAULT 0,
                    motion_detected BOOLEAN DEFAULT FALSE,
                    confidence REAL DEFAULT 0.0,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_dashboard ON analytics(timestamp DESC, camera_id, tenant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_camera ON analytics(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_tenant ON analytics(tenant_id)")
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    visitor_count INTEGER DEFAULT 0,
                    motion_detected BOOLEAN DEFAULT FALSE,
                    confidence REAL DEFAULT 0.0,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON analytics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_dashboard ON analytics(timestamp DESC, camera_id, tenant_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_camera ON analytics(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tenant ON analytics(tenant_id)")
        
        # Heatmaps table
        if DB_TYPE == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS heatmaps (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    heatmap_path TEXT NOT NULL,
                    hotspot_count INTEGER DEFAULT 0,
                    max_density REAL DEFAULT 0.0,
                    avg_motion REAL DEFAULT 0.0,
                    grid_data TEXT DEFAULT '',
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_timestamp ON heatmaps(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_camera ON heatmaps(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_tenant ON heatmaps(tenant_id)")
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS heatmaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    heatmap_path TEXT NOT NULL,
                    hotspot_count INTEGER DEFAULT 0,
                    max_density REAL DEFAULT 0.0,
                    avg_motion REAL DEFAULT 0.0,
                    grid_data TEXT DEFAULT '',
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_timestamp ON heatmaps(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_camera ON heatmaps(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_heatmap_tenant ON heatmaps(tenant_id)")
        
        # Tracking events table
        if DB_TYPE == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracking_events (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    object_count INTEGER DEFAULT 0,
                    trajectories TEXT DEFAULT '',
                    avg_speed REAL DEFAULT 0.0,
                    max_objects INTEGER DEFAULT 0,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_timestamp ON tracking_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_camera ON tracking_events(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_tenant ON tracking_events(tenant_id)")
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracking_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    object_count INTEGER DEFAULT 0,
                    trajectories TEXT DEFAULT '',
                    avg_speed REAL DEFAULT 0.0,
                    max_objects INTEGER DEFAULT 0,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_timestamp ON tracking_events(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_camera ON tracking_events(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_tenant ON tracking_events(tenant_id)")
        
        # Person detections table
        if DB_TYPE == "postgres":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS person_detections (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    total_detections INTEGER DEFAULT 0,
                    max_people INTEGER DEFAULT 0,
                    avg_people REAL DEFAULT 0.0,
                    detections_json TEXT DEFAULT '',
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_timestamp ON person_detections(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_camera ON person_detections(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_tenant ON person_detections(tenant_id)")
            
            # Processed files table for atomic tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    filename TEXT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    processed_at TIMESTAMPTZ DEFAULT NOW(),
                    camera_id TEXT,
                    metadata_json TEXT,
                    PRIMARY KEY (filename, tenant_id),
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS person_detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    camera_name TEXT DEFAULT '',
                    camera_location TEXT DEFAULT '',
                    filename TEXT NOT NULL,
                    total_detections INTEGER DEFAULT 0,
                    max_people INTEGER DEFAULT 0,
                    avg_people REAL DEFAULT 0.0,
                    detections_json TEXT DEFAULT '',
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (camera_id, tenant_id) REFERENCES cameras(id, tenant_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_timestamp ON person_detections(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_camera ON person_detections(camera_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_tenant ON person_detections(tenant_id)")
            
            # Processed files for SQLite
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    filename TEXT,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    camera_id TEXT,
                    metadata_json TEXT,
                    PRIMARY KEY (filename, tenant_id)
                )
            """)
        
        conn.commit()


def save_result(
    db_path: Path,
    camera_id: str,
    filename: str,
    visitor_count: int,
    motion_detected: bool = False,
    confidence: float = 0.0,
    camera_name: str = "",
    camera_location: str = "",
    tenant_id: str = "default"
) -> int:
    """Save an analytics result to the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                INSERT INTO analytics (timestamp, camera_id, camera_name, camera_location, 
                                       filename, visitor_count, motion_detected, confidence, tenant_id)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, camera_name, camera_location, 
                  filename, visitor_count, motion_detected, confidence, tenant_id))
            row_id = cursor.fetchone()[0]
        else:
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO analytics (timestamp, camera_id, camera_name, camera_location, 
                                       filename, visitor_count, motion_detected, confidence, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, camera_id, camera_name, camera_location, 
                  filename, visitor_count, motion_detected, confidence, tenant_id))
            row_id = cursor.lastrowid
        
        conn.commit()
        return row_id


def get_results(db_path: Path, limit: int = 100, offset: int = 0, camera_id: Optional[str] = None, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieve the latest analytics results with pagination support."""
    limit = min(limit, MAX_LIMIT)
    with get_connection() as conn:
        if DB_TYPE == "postgres":
            conn.row_factory = psycopg2.extras.RealDictCursor
        cursor = conn.cursor()
        
        # Select specific columns for better performance
        columns = "id, timestamp, camera_id, camera_name, camera_location, filename, visitor_count, motion_detected, confidence"
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute(f"""
                    SELECT {columns} FROM analytics
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """, (camera_id, tenant_id, limit, offset))
            else:
                cursor.execute(f"""
                    SELECT {columns} FROM analytics
                    WHERE camera_id = ? AND tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (camera_id, tenant_id, limit, offset))
        else:
            if DB_TYPE == "postgres":
                cursor.execute(f"""
                    SELECT {columns} FROM analytics
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                """, (tenant_id, limit, offset))
            else:
                cursor.execute(f"""
                    SELECT {columns} FROM analytics
                    WHERE tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (tenant_id, limit, offset))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_results_count(db_path: Path, camera_id: Optional[str] = None, tenant_id: str = "default") -> int:
    """Get total number of analytics results for pagination."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE camera_id = %s AND tenant_id = %s", (camera_id, tenant_id))
            else:
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE camera_id = ? AND tenant_id = ?", (camera_id, tenant_id))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE tenant_id = %s", (tenant_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE tenant_id = ?", (tenant_id,))
        
        return cursor.fetchone()[0]


def get_stats(db_path: Path, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
    """Get summary statistics from the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        COALESCE(SUM(visitor_count), 0) as total_visitors,
                        COALESCE(AVG(confidence), 0) as avg_confidence,
                        COALESCE(SUM(CASE WHEN motion_detected THEN 1 ELSE 0 END), 0) as motion_events
                    FROM analytics
                    WHERE camera_id = %s AND tenant_id = %s
                """, (camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        COALESCE(SUM(visitor_count), 0) as total_visitors,
                        COALESCE(AVG(confidence), 0) as avg_confidence,
                        COALESCE(SUM(CASE WHEN motion_detected THEN 1 ELSE 0 END), 0) as motion_events
                    FROM analytics
                    WHERE camera_id = ? AND tenant_id = ?
                """, (camera_id, tenant_id))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        COALESCE(SUM(visitor_count), 0) as total_visitors,
                        COALESCE(AVG(confidence), 0) as avg_confidence,
                        COALESCE(SUM(CASE WHEN motion_detected THEN 1 ELSE 0 END), 0) as motion_events
                    FROM analytics
                    WHERE tenant_id = %s
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        COALESCE(SUM(visitor_count), 0) as total_visitors,
                        COALESCE(AVG(confidence), 0) as avg_confidence,
                        COALESCE(SUM(CASE WHEN motion_detected THEN 1 ELSE 0 END), 0) as motion_events
                    FROM analytics
                    WHERE tenant_id = ?
                """, (tenant_id,))
        
        row = cursor.fetchone()
        return {
            "total_events": row[0],
            "total_visitors": row[1],
            "avg_confidence": round(row[2], 2),
            "motion_events": row[3]
        }


def get_hourly_counts(db_path: Path, hours: int = 24, camera_id: Optional[str] = None, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Get visitor counts grouped by hour."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            if camera_id:
                cursor.execute("""
                    SELECT 
                        TO_CHAR(timestamp, 'YYYY-MM-DD HH24:00') as hour,
                        SUM(visitor_count) as visitors,
                        COUNT(*) as events
                    FROM analytics
                    WHERE timestamp >= NOW() - INTERVAL '%s hours'
                      AND camera_id = %s AND tenant_id = %s
                    GROUP BY hour
                    ORDER BY hour
                """, (hours, camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        TO_CHAR(timestamp, 'YYYY-MM-DD HH24:00') as hour,
                        SUM(visitor_count) as visitors,
                        COUNT(*) as events
                    FROM analytics
                    WHERE timestamp >= NOW() - INTERVAL '%s hours'
                      AND tenant_id = %s
                    GROUP BY hour
                    ORDER BY hour
                """, (hours, tenant_id))
        else:
            if camera_id:
                cursor.execute("""
                    SELECT 
                        strftime('%Y-%m-%d %H:00', timestamp) as hour,
                        SUM(visitor_count) as visitors,
                        COUNT(*) as events
                    FROM analytics
                    WHERE timestamp >= datetime('now', ? || ' hours')
                      AND camera_id = ? AND tenant_id = ?
                    GROUP BY hour
                    ORDER BY hour
                """, (f"-{hours}", camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        strftime('%Y-%m-%d %H:00', timestamp) as hour,
                        SUM(visitor_count) as visitors,
                        COUNT(*) as events
                    FROM analytics
                    WHERE timestamp >= datetime('now', ? || ' hours')
                      AND tenant_id = ?
                    GROUP BY hour
                    ORDER BY hour
                """, (f"-{hours}", tenant_id))
        
        rows = cursor.fetchall()
        return [{"hour": row[0], "visitors": row[1], "events": row[2]} for row in rows]


def get_cameras(db_path: Path, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Get list of all cameras that have recorded data for this tenant."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                SELECT 
                    camera_id,
                    MAX(camera_name) as camera_name,
                    MAX(camera_location) as camera_location,
                    COUNT(*) as event_count,
                    MAX(timestamp) as last_event
                FROM analytics
                WHERE tenant_id = %s
                GROUP BY camera_id
                ORDER BY last_event DESC
            """, (tenant_id,))
        else:
            cursor.execute("""
                SELECT 
                    camera_id,
                    MAX(camera_name) as camera_name,
                    MAX(camera_location) as camera_location,
                    COUNT(*) as event_count,
                    MAX(timestamp) as last_event
                FROM analytics
                WHERE tenant_id = ?
                GROUP BY camera_id
                ORDER BY last_event DESC
            """, (tenant_id,))
        
        rows = cursor.fetchall()
        return [{
            "camera_id": row[0],
            "camera_name": row[1] or row[0],
            "camera_location": row[2] or "Unknown",
            "event_count": row[3],
            "last_event": str(row[4])
        } for row in rows]


def get_camera_stats(db_path: Path, camera_id: str, tenant_id: str = "default") -> Dict[str, Any]:
    """Get detailed statistics for a specific camera."""
    stats = get_stats(db_path, camera_id=camera_id, tenant_id=tenant_id)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                SELECT 
                    MAX(camera_name) as camera_name,
                    MAX(camera_location) as camera_location,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event
                FROM analytics
                WHERE camera_id = %s AND tenant_id = %s
            """, (camera_id, tenant_id))
        else:
            cursor.execute("""
                SELECT 
                    MAX(camera_name) as camera_name,
                    MAX(camera_location) as camera_location,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event
                FROM analytics
                WHERE camera_id = ? AND tenant_id = ?
            """, (camera_id, tenant_id))
        
        row = cursor.fetchone()
        stats["camera_id"] = camera_id
        stats["camera_name"] = row[0] or camera_id
        stats["camera_location"] = row[1] or "Unknown"
        stats["first_event"] = str(row[2])
        stats["last_event"] = str(row[3])
        
        return stats


# ============================================
# Heatmap Model Functions
# ============================================

def save_heatmap(
    db_path: Path,
    camera_id: str,
    filename: str,
    heatmap_path: str,
    hotspot_count: int = 0,
    max_density: float = 0.0,
    avg_motion: float = 0.0,
    camera_name: str = "",
    camera_location: str = "",
    tenant_id: str = "default"
) -> int:
    """Save heatmap results to database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                INSERT INTO heatmaps (timestamp, camera_id, camera_name, camera_location,
                                      filename, heatmap_path, hotspot_count, max_density, avg_motion, tenant_id)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, camera_name, camera_location,
                  filename, heatmap_path, hotspot_count, max_density, avg_motion, tenant_id))
            row_id = cursor.fetchone()[0]
        else:
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO heatmaps (timestamp, camera_id, camera_name, camera_location,
                                      filename, heatmap_path, hotspot_count, max_density, avg_motion, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, camera_id, camera_name, camera_location,
                  filename, heatmap_path, hotspot_count, max_density, avg_motion, tenant_id))
            row_id = cursor.lastrowid
        
        conn.commit()
        return row_id


def get_heatmaps(db_path: Path, limit: int = 100, camera_id: Optional[str] = None, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieve heatmap results."""
    limit = min(limit, MAX_LIMIT)
    with get_connection() as conn:
        if DB_TYPE == "postgres":
            conn.row_factory = psycopg2.extras.RealDictCursor
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM heatmaps
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM heatmaps
                    WHERE camera_id = ? AND tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (camera_id, tenant_id, limit))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM heatmaps
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM heatmaps
                    WHERE tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (tenant_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_heatmap_stats(db_path: Path, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
    """Get heatmap statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_heatmaps,
                        AVG(hotspot_count) as avg_hotspots,
                        MAX(max_density) as peak_density,
                        AVG(avg_motion) as overall_motion
                    FROM heatmaps
                    WHERE camera_id = %s AND tenant_id = %s
                """, (camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_heatmaps,
                        AVG(hotspot_count) as avg_hotspots,
                        MAX(max_density) as peak_density,
                        AVG(avg_motion) as overall_motion
                    FROM heatmaps
                    WHERE camera_id = ? AND tenant_id = ?
                """, (camera_id, tenant_id))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_heatmaps,
                        AVG(hotspot_count) as avg_hotspots,
                        MAX(max_density) as peak_density,
                        AVG(avg_motion) as overall_motion
                    FROM heatmaps
                    WHERE tenant_id = %s
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_heatmaps,
                        AVG(hotspot_count) as avg_hotspots,
                        MAX(max_density) as peak_density,
                        AVG(avg_motion) as overall_motion
                    FROM heatmaps
                    WHERE tenant_id = ?
                """, (tenant_id,))
        
        row = cursor.fetchone()
        return {
            "total_heatmaps": row[0],
            "avg_hotspots": round(row[1] or 0, 2),
            "peak_density": round(row[2] or 0, 2),
            "overall_motion": round(row[3] or 0, 2)
        }


# ============================================
# Tracking Model Functions
# ============================================

def save_tracking_event(
    db_path: Path,
    camera_id: str,
    filename: str,
    object_count: int = 0,
    trajectories: str = "",
    avg_speed: float = 0.0,
    max_objects: int = 0,
    camera_name: str = "",
    camera_location: str = "",
    tenant_id: str = "default"
) -> int:
    """Save tracking results to database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                INSERT INTO tracking_events (timestamp, camera_id, camera_name, camera_location,
                                              filename, object_count, trajectories, avg_speed, max_objects, tenant_id)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, camera_name, camera_location,
                  filename, object_count, trajectories, avg_speed, max_objects, tenant_id))
            row_id = cursor.fetchone()[0]
        else:
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO tracking_events (timestamp, camera_id, camera_name, camera_location,
                                              filename, object_count, trajectories, avg_speed, max_objects, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, camera_id, camera_name, camera_location,
                  filename, object_count, trajectories, avg_speed, max_objects, tenant_id))
            row_id = cursor.lastrowid
        
        conn.commit()
        return row_id


def get_tracking_events(db_path: Path, limit: int = 100, camera_id: Optional[str] = None, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieve tracking events."""
    limit = min(limit, MAX_LIMIT)
    with get_connection() as conn:
        if DB_TYPE == "postgres":
            conn.row_factory = psycopg2.extras.RealDictCursor
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM tracking_events
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM tracking_events
                    WHERE camera_id = ? AND tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (camera_id, tenant_id, limit))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM tracking_events
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM tracking_events
                    WHERE tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (tenant_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_tracking_stats(db_path: Path, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
    """Get tracking statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        SUM(object_count) as total_objects,
                        AVG(avg_speed) as avg_speed,
                        MAX(max_objects) as peak_objects
                    FROM tracking_events
                    WHERE camera_id = %s AND tenant_id = %s
                """, (camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        SUM(object_count) as total_objects,
                        AVG(avg_speed) as avg_speed,
                        MAX(max_objects) as peak_objects
                    FROM tracking_events
                    WHERE camera_id = ? AND tenant_id = ?
                """, (camera_id, tenant_id))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        SUM(object_count) as total_objects,
                        AVG(avg_speed) as avg_speed,
                        MAX(max_objects) as peak_objects
                    FROM tracking_events
                    WHERE tenant_id = %s
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_events,
                        SUM(object_count) as total_objects,
                        AVG(avg_speed) as avg_speed,
                        MAX(max_objects) as peak_objects
                    FROM tracking_events
                    WHERE tenant_id = ?
                """, (tenant_id,))
        
        row = cursor.fetchone()
        return {
            "total_events": row[0],
            "total_objects": row[1] or 0,
            "avg_speed": round(row[2] or 0, 2),
            "peak_objects": row[3] or 0
        }


# ============================================
# Person Detection Model Functions
# ============================================

def save_person_detection(
    db_path: Path,
    camera_id: str,
    filename: str,
    total_detections: int = 0,
    max_people: int = 0,
    avg_people: float = 0.0,
    detections_json: str = "",
    camera_name: str = "",
    camera_location: str = "",
    tenant_id: str = "default"
) -> int:
    """Save person detection results to database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if DB_TYPE == "postgres":
            cursor.execute("""
                INSERT INTO person_detections (timestamp, camera_id, camera_name, camera_location,
                                               filename, total_detections, max_people, avg_people, detections_json, tenant_id)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, camera_name, camera_location,
                  filename, total_detections, max_people, avg_people, detections_json, tenant_id))
            row_id = cursor.fetchone()[0]
        else:
            timestamp = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO person_detections (timestamp, camera_id, camera_name, camera_location,
                                               filename, total_detections, max_people, avg_people, detections_json, tenant_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, camera_id, camera_name, camera_location,
                  filename, total_detections, max_people, avg_people, detections_json, tenant_id))
            row_id = cursor.lastrowid
        
        conn.commit()
        return row_id


def get_person_detections(db_path: Path, limit: int = 100, camera_id: Optional[str] = None, tenant_id: str = "default") -> List[Dict[str, Any]]:
    """Retrieve person detection results."""
    limit = min(limit, MAX_LIMIT)
    with get_connection() as conn:
        if DB_TYPE == "postgres":
            conn.row_factory = psycopg2.extras.RealDictCursor
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM person_detections
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM person_detections
                    WHERE camera_id = ? AND tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (camera_id, tenant_id, limit))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT * FROM person_detections
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM person_detections
                    WHERE tenant_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (tenant_id, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_person_detection_stats(db_path: Path, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
    """Get person detection statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if camera_id:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(total_detections) as total_detections,
                        MAX(max_people) as peak_occupancy,
                        AVG(avg_people) as avg_people
                    FROM person_detections
                    WHERE camera_id = %s AND tenant_id = %s
                """, (camera_id, tenant_id))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(total_detections) as total_detections,
                        MAX(max_people) as peak_occupancy,
                        AVG(avg_people) as avg_people
                    FROM person_detections
                    WHERE camera_id = ? AND tenant_id = ?
                """, (camera_id, tenant_id))
        else:
            if DB_TYPE == "postgres":
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(total_detections) as total_detections,
                        MAX(max_people) as peak_occupancy,
                        AVG(avg_people) as avg_people
                    FROM person_detections
                    WHERE tenant_id = %s
                """, (tenant_id,))
            else:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_videos,
                        SUM(total_detections) as total_detections,
                        MAX(max_people) as peak_occupancy,
                        AVG(avg_people) as avg_people
                    FROM person_detections
                    WHERE tenant_id = ?
                """, (tenant_id,))
        
        row = cursor.fetchone()
        return {
            "total_videos": row[0],
            "total_detections": row[1] or 0,
            "peak_occupancy": row[2] or 0,
            "avg_people": round(row[3] or 0, 2)
        }
