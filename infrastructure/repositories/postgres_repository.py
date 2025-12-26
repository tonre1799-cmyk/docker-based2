"""
PostgreSQL Repository Implementation
====================================
Implements all repository interfaces for PostgreSQL database.
This is the main production adapter.
"""

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

from core.interfaces.repository import (
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository,
    CameraRepository
)

logger = logging.getLogger(__name__)


class PostgresRepository(
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository,
    CameraRepository
):
    """
    PostgreSQL implementation of all repository interfaces.
    
    Consolidates data access into a single adapter that implements
    all the repository interfaces.
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None
    ):
        """
        Initialize PostgreSQL connection settings.
        Falls back to environment variables if not provided.
        """
        self.host = host or os.environ.get("POSTGRES_HOST", "localhost")
        self.port = port or int(os.environ.get("POSTGRES_PORT", "5432"))
        self.database = database or os.environ.get("POSTGRES_DB", "analytics")
        self.user = user or os.environ.get("POSTGRES_USER", "analytics_user")
        self.password = password or os.environ.get("POSTGRES_PASSWORD", "analytics_pass")
        
        self.max_limit = int(os.environ.get("MAX_DB_LIMIT", 1000))
        self._pool = None
        self._schema_initialized = False
    
    def _get_pool(self):
        """Initialize connection pool."""
        if self._pool is None:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
        return self._pool
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections using pool."""
        if not HAS_POSTGRES:
            raise ImportError("psycopg2 is required for PostgreSQL support")
        
        pool = self._get_pool()
        conn = None
        try:
            conn = pool.getconn()
            yield conn
        finally:
            if conn:
                pool.putconn(conn)
    
    @contextmanager
    def _get_cursor(self, dict_cursor: bool = True):
        """Context manager for database cursors."""
        with self._get_connection() as conn:
            cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    @contextmanager
    def _get_transaction(self, dict_cursor: bool = False):
        """
        Context manager for explicit transactions.
        Ensures commit on success and rollback on failure.
        """
        with self._get_connection() as conn:
            cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    # ==========================================
    # BaseRepository Implementation
    # ==========================================
    
    def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def init_schema(self) -> None:
        """
        Database schema for PostgreSQL is managed by Alembic migrations.
        This method is kept for interface compatibility but performs no actions.
        """
        logger.info("PostgreSQL schema initialization deferred to Alembic migrations.")
        self._schema_initialized = True
    
    # ==========================================
    # AnalyticsRepository Implementation
    # ==========================================
    
    def save_result(
        self,
        camera_id: str,
        filename: str,
        visitor_count: int,
        motion_detected: bool = False,
        confidence: float = 0.0,
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save an analytics result."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("""
                INSERT INTO analytics 
                (camera_id, filename, visitor_count, motion_detected, confidence, camera_name, camera_location, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, filename, visitor_count, motion_detected, confidence, camera_name, camera_location, tenant_id))
            return cursor.fetchone()[0]
    
    def get_results(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve analytics results."""
        limit = min(limit, self.max_limit)
        with self._get_cursor() as cursor:
            if camera_id:
                cursor.execute("""
                    SELECT * FROM analytics 
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM analytics 
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (tenant_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
        """Get summary statistics."""
        with self._get_cursor(dict_cursor=False) as cursor:
            query = """
                SELECT 
                    COUNT(*) as total_events,
                    COALESCE(SUM(visitor_count), 0) as total_visitors,
                    COALESCE(AVG(confidence), 0) as avg_confidence,
                    COALESCE(SUM(CASE WHEN motion_detected THEN 1 ELSE 0 END), 0) as motion_events
                FROM analytics
                WHERE tenant_id = %s
            """
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            cursor.execute(query, tuple(params))
            
            row = cursor.fetchone()
            return {
                "total_events": row[0],
                "total_visitors": row[1],
                "avg_confidence": round(float(row[2]), 2),
                "motion_events": row[3]
            }

    def get_results_count(self, camera_id=None, tenant_id="default") -> int:
        """Get total count of analytics results."""
        with self._get_cursor() as cursor:
            query = "SELECT COUNT(*) FROM analytics WHERE tenant_id = %s"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def get_camera_stats(self, tenant_id="default") -> List[Dict[str, Any]]:
        """Get performance metrics per camera."""
        with self._get_cursor() as cursor:
            query = """
                SELECT 
                    camera_id, 
                    MAX(camera_name) as name, 
                    COUNT(*) as events, 
                    SUM(visitor_count) as visitors,
                    AVG(confidence) as avg_conf
                FROM analytics 
                WHERE tenant_id = %s 
                GROUP BY camera_id 
                ORDER BY visitors DESC
            """
            cursor.execute(query, (tenant_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_hourly_counts(
        self,
        hours: int = 24,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get visitor counts grouped by hour."""
        with self._get_cursor() as cursor:
            query = """
                SELECT 
                    date_trunc('hour', timestamp) as hour,
                    SUM(visitor_count) as visitors,
                    COUNT(*) as events
                FROM analytics
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                AND tenant_id = %s
            """
            params = [hours, tenant_id]
            
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            
            query += " GROUP BY hour ORDER BY hour"
            cursor.execute(query, tuple(params))
            
            return [
                {
                    "hour": str(row["hour"]),
                    "visitors": row["visitors"],
                    "events": row["events"]
                }
                for row in cursor.fetchall()
            ]
    
    def get_cameras(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """Get list of cameras with recorded data."""
        with self._get_cursor() as cursor:
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
            return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================
    # HeatmapRepository Implementation
    # ==========================================
    
    def save_heatmap(
        self,
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
        """Save heatmap results."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("""
                INSERT INTO heatmaps 
                (camera_id, filename, heatmap_path, hotspot_count, max_density, avg_motion, camera_name, camera_location, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, filename, heatmap_path, hotspot_count, max_density, avg_motion, camera_name, camera_location, tenant_id))
            return cursor.fetchone()[0]
    
    def get_heatmaps(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve heatmap results."""
        limit = min(limit, self.max_limit)
        with self._get_cursor() as cursor:
            query = "SELECT * FROM heatmaps WHERE tenant_id = %s"
            params = [tenant_id]
            
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            
            if start_date:
                query += " AND timestamp >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= %s"
                params.append(end_date)
                
            query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_heatmap_stats(self, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
        """Get heatmap statistics."""
        with self._get_cursor(dict_cursor=False) as cursor:
            query = """
                SELECT 
                    COUNT(*) as total_heatmaps,
                    COALESCE(AVG(hotspot_count), 0) as avg_hotspots,
                    COALESCE(MAX(max_density), 0) as max_density,
                    COALESCE(AVG(avg_motion), 0) as avg_motion
                FROM heatmaps
                WHERE tenant_id = %s
            """
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            
            cursor.execute(query, tuple(params))
            
            row = cursor.fetchone()
            return {
                "total_heatmaps": row[0],
                "avg_hotspots": round(float(row[1]), 1),
                "max_density": round(float(row[2]), 2),
                "avg_motion": round(float(row[3]), 2)
            }
    
    # ==========================================
    # TrackingRepository Implementation
    # ==========================================
    
    def save_tracking_event(
        self,
        camera_id: str,
        filename: str,
        object_count: int = 0,
        trajectories: str = "",
        avg_speed: float = 0.0,
        max_objects: int = 0,
        entries: int = 0,
        exits: int = 0,
        camera_name: str = "",
        camera_location: str = "",
        tenant_id: str = "default"
    ) -> int:
        """Save tracking results."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("""
                INSERT INTO tracking_events 
                (camera_id, filename, object_count, trajectories, avg_speed, max_objects, entries, exits, camera_name, camera_location, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, filename, object_count, trajectories, avg_speed, max_objects, entries, exits, camera_name, camera_location, tenant_id))
            return cursor.fetchone()[0]
    
    def get_tracking_events(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve tracking events."""
        with self._get_cursor() as cursor:
            if camera_id:
                cursor.execute("""
                    SELECT * FROM tracking_events 
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM tracking_events 
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (tenant_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_tracking_stats(self, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
        """Get tracking statistics."""
        with self._get_cursor(dict_cursor=False) as cursor:
            query = """
                SELECT 
                    COUNT(*) as total_events,
                    COALESCE(SUM(object_count), 0) as total_objects,
                    COALESCE(AVG(avg_speed), 0) as avg_speed,
                    COALESCE(MAX(max_objects), 0) as peak_objects,
                    COALESCE(SUM(entries), 0) as total_entries,
                    COALESCE(SUM(exits), 0) as total_exits
                FROM tracking_events
                WHERE tenant_id = %s
            """
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            
            cursor.execute(query, tuple(params))
            
            row = cursor.fetchone()
            return {
                "total_events": row[0],
                "total_objects": row[1],
                "avg_speed": round(float(row[2]), 1),
                "peak_objects": row[3],
                "total_entries": row[4],
                "total_exits": row[5]
            }
    
    # ==========================================
    # PersonDetectionRepository Implementation
    # ==========================================
    
    def save_person_detection(
        self,
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
        """Save person detection results."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("""
                INSERT INTO person_detections 
                (camera_id, filename, total_detections, max_people, avg_people, detections_json, camera_name, camera_location, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (camera_id, filename, total_detections, max_people, avg_people, detections_json, camera_name, camera_location, tenant_id))
            return cursor.fetchone()[0]
    
    def get_person_detections(
        self,
        limit: int = 100,
        camera_id: Optional[str] = None,
        tenant_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """Retrieve person detection results."""
        with self._get_cursor() as cursor:
            if camera_id:
                cursor.execute("""
                    SELECT * FROM person_detections 
                    WHERE camera_id = %s AND tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (camera_id, tenant_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM person_detections 
                    WHERE tenant_id = %s
                    ORDER BY timestamp DESC LIMIT %s
                """, (tenant_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_person_detection_stats(self, camera_id: Optional[str] = None, tenant_id: str = "default") -> Dict[str, Any]:
        """Get person detection statistics."""
        with self._get_cursor(dict_cursor=False) as cursor:
            query = """
                SELECT 
                    COUNT(*) as total_videos,
                    COALESCE(SUM(total_detections), 0) as total_detections,
                    COALESCE(MAX(max_people), 0) as peak_occupancy,
                    COALESCE(AVG(avg_people), 0) as avg_people
                FROM person_detections
                WHERE tenant_id = %s
            """
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = %s"
                params.append(camera_id)
            
            cursor.execute(query, tuple(params))
            
            row = cursor.fetchone()
            return {
                "total_videos": row[0],
                "total_detections": row[1],
                "peak_occupancy": row[2],
                "avg_people": round(float(row[3]), 1)
            }
    
    # ==========================================
    # CameraRepository Implementation
    # ==========================================
    
    def save_camera(
        self,
        camera_id: str,
        name: str,
        location: str,
        ip: str,
        port: int = 81,
        enabled: bool = True,
        tenant_id: str = "default"
    ) -> str:
        """Save or update camera."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("""
                INSERT INTO cameras (id, name, location, ip, port, enabled, tenant_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id, tenant_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    location = EXCLUDED.location,
                    ip = EXCLUDED.ip,
                    port = EXCLUDED.port,
                    enabled = EXCLUDED.enabled,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (camera_id, name, location, ip, port, enabled, tenant_id))
            return cursor.fetchone()[0]
    
    def get_camera(self, camera_id: str, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        """Get camera by ID."""
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT id, name, location, ip, port, enabled FROM cameras WHERE id = %s AND tenant_id = %s",
                (camera_id, tenant_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_cameras(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        """List all cameras."""
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT id, name, location, ip, port, enabled FROM cameras WHERE tenant_id = %s ORDER BY created_at DESC",
                (tenant_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_camera(self, camera_id: str, tenant_id: str = "default") -> bool:
        """Delete camera."""
        with self._get_transaction(dict_cursor=False) as cursor:
            cursor.execute("DELETE FROM cameras WHERE id = %s AND tenant_id = %s", (camera_id, tenant_id))
            return cursor.rowcount > 0

    # ==========================================
    # ProcessedFilesRepository Implementation
    # ==========================================

    def is_processed(self, filename: str, tenant_id: str = "default") -> bool:
        """Check if a file has already been processed."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT 1 FROM processed_files WHERE filename = %s AND tenant_id = %s", (filename, tenant_id))
            return cursor.fetchone() is not None

    def mark_processed(
        self,
        filename: str,
        camera_id: str,
        tenant_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Mark a file as processed. Returns True if successfully marked (atomic)."""
        try:
            with self._get_transaction(dict_cursor=False) as cursor:
                cursor.execute("""
                    INSERT INTO processed_files (filename, camera_id, tenant_id, metadata_json)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (filename, tenant_id) DO NOTHING
                """, (filename, camera_id, tenant_id, json.dumps(metadata) if metadata else None))
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark file as processed: {e}")
            return False
