"""
SQLite Repository Implementation
==============================
Implements repository interfaces for SQLite database.
Used primarily for local development and edge deployments.
"""

import sqlite3
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from core.interfaces.repository import (
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository,
    CameraRepository
)

logger = logging.getLogger(__name__)


class SqliteRepository(
    AnalyticsRepository,
    HeatmapRepository,
    TrackingRepository,
    PersonDetectionRepository,
    CameraRepository
):
    """
    Unified SQLite repository implementation.
    Implements all analytic repository interfaces for SQLite.
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.max_limit = 1000
    
    @contextmanager
    def _get_connection(self):
        """Get SQLite connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager
    def _get_cursor(self, conn):
        """Get cursor and handle commits."""
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def health_check(self) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"SQLite health check failed: {e}")
            return False

    def init_schema(self) -> None:
        """Initialize SQLite schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                # Analytics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        camera_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        visitor_count INTEGER DEFAULT 0,
                        motion_detected BOOLEAN DEFAULT 0,
                        confidence REAL DEFAULT 0.0,
                        camera_name TEXT,
                        camera_location TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Heatmaps table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS heatmaps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        camera_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        heatmap_path TEXT,
                        hotspot_count INTEGER DEFAULT 0,
                        max_density REAL DEFAULT 0.0,
                        avg_motion REAL DEFAULT 0.0,
                        camera_name TEXT,
                        camera_location TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tracking events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tracking_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        camera_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        object_count INTEGER DEFAULT 0,
                        trajectories TEXT,
                        avg_speed REAL DEFAULT 0.0,
                        max_objects INTEGER DEFAULT 0,
                        entries INTEGER DEFAULT 0,
                        exits INTEGER DEFAULT 0,
                        camera_name TEXT,
                        camera_location TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Person detections table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS person_detections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        camera_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        total_detections INTEGER DEFAULT 0,
                        max_people INTEGER DEFAULT 0,
                        avg_people REAL DEFAULT 0.0,
                        detections_json TEXT,
                        camera_name TEXT,
                        camera_location TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Cameras table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cameras (
                        id TEXT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        name TEXT NOT NULL,
                        location TEXT NOT NULL,
                        ip TEXT NOT NULL,
                        port INTEGER DEFAULT 81,
                        enabled BOOLEAN DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (id, tenant_id)
                    )
                """)

                # Processed files table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_files (
                        filename TEXT,
                        tenant_id TEXT NOT NULL DEFAULT 'default',
                        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        camera_id TEXT,
                        metadata_json TEXT,
                        PRIMARY KEY (filename, tenant_id)
                    )
                """)

                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_tenant_ts ON analytics(tenant_id, timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_analytics_cam ON analytics(camera_id)")

    # AnalyticsRepository Implementation
    
    def save_result(self, camera_id, filename, visitor_count, motion_detected=False, confidence=0.0, camera_name="", camera_location="", tenant_id="default") -> int:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO analytics (camera_id, filename, visitor_count, motion_detected, confidence, camera_name, camera_location, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (camera_id, filename, visitor_count, 1 if motion_detected else 0, confidence, camera_name, camera_location, tenant_id))
                return cursor.lastrowid

    def get_results(self, limit=100, camera_id=None, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM analytics WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_stats(self, camera_id=None, tenant_id="default") -> Dict[str, Any]:
        with self._get_connection() as conn:
            query = "SELECT COUNT(*) as events, SUM(visitor_count) as visitors, AVG(confidence) as conf, SUM(motion_detected) as motion FROM analytics WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            row = conn.execute(query, params).fetchone()
            return {
                "total_events": row['events'] or 0,
                "total_visitors": row['visitors'] or 0,
                "avg_confidence": round(row['conf'] or 0.0, 2),
                "motion_events": row['motion'] or 0
            }

    def get_hourly_counts(self, hours=24, camera_id=None, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = """
                SELECT strftime('%Y-%m-%d %H:00:00', timestamp) as hour, SUM(visitor_count) as visitors, COUNT(*) as events
                FROM analytics
                WHERE timestamp >= datetime('now', ?) AND tenant_id = ?
            """
            params = [f"-{hours} hours", tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            query += " GROUP BY hour ORDER BY hour"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_cameras(self, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT camera_id, MAX(camera_name) as camera_name, MAX(camera_location) as camera_location, COUNT(*) as event_count, MAX(timestamp) as last_event
                FROM analytics WHERE tenant_id = ? GROUP BY camera_id ORDER BY last_event DESC
            """, (tenant_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_results_count(self, camera_id=None, tenant_id="default") -> int:
        """Get total count of analytics results."""
        with self._get_connection() as conn:
            query = "SELECT COUNT(*) FROM analytics WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            row = conn.execute(query, params).fetchone()
            return row[0] if row else 0

    def get_camera_stats(self, tenant_id="default") -> List[Dict[str, Any]]:
        """Get performance metrics per camera."""
        with self._get_connection() as conn:
            query = """
                SELECT 
                    camera_id, 
                    MAX(camera_name) as name, 
                    COUNT(*) as events, 
                    SUM(visitor_count) as visitors,
                    AVG(confidence) as avg_conf
                FROM analytics 
                WHERE tenant_id = ? 
                GROUP BY camera_id 
                ORDER BY visitors DESC
            """
            rows = conn.execute(query, (tenant_id,)).fetchall()
            return [dict(r) for r in rows]

    # HeatmapRepository Implementation
    
    def save_heatmap(self, camera_id, filename, heatmap_path, hotspot_count=0, max_density=0.0, avg_motion=0.0, camera_name="", camera_location="", tenant_id="default") -> int:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO heatmaps (camera_id, filename, heatmap_path, hotspot_count, max_density, avg_motion, camera_name, camera_location, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (camera_id, filename, heatmap_path, hotspot_count, max_density, avg_motion, camera_name, camera_location, tenant_id))
                return cursor.lastrowid

    def get_heatmaps(self, limit=100, camera_id=None, start_date=None, end_date=None, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM heatmaps WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_heatmap_stats(self, camera_id=None, tenant_id="default") -> Dict[str, Any]:
        with self._get_connection() as conn:
            query = "SELECT COUNT(*) as count, AVG(hotspot_count) as avg_spots, MAX(max_density) as max_dens FROM heatmaps WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            row = conn.execute(query, params).fetchone()
            return {
                "total_heatmaps": row['count'] or 0,
                "avg_hotspots": round(row['avg_spots'] or 0.0, 1),
                "max_density": round(row['max_dens'] or 0.0, 2)
            }

    # TrackingRepository Implementation

    def save_tracking_event(self, camera_id, filename, object_count=0, trajectories="", avg_speed=0.0, max_objects=0, entries=0, exits=0, camera_name="", camera_location="", tenant_id="default") -> int:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO tracking_events (camera_id, filename, object_count, trajectories, avg_speed, max_objects, entries, exits, camera_name, camera_location, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (camera_id, filename, object_count, trajectories, avg_speed, max_objects, entries, exits, camera_name, camera_location, tenant_id))
                return cursor.lastrowid

    def get_tracking_events(self, limit=100, camera_id=None, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM tracking_events WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_tracking_stats(self, camera_id=None, tenant_id="default") -> Dict[str, Any]:
        with self._get_connection() as conn:
            query = "SELECT COUNT(*) as count, SUM(object_count) as objects, AVG(avg_speed) as speed FROM tracking_events WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            row = conn.execute(query, params).fetchone()
            return {
                "total_events": row['count'] or 0,
                "total_objects": row['objects'] or 0,
                "avg_speed": round(row['speed'] or 0.0, 1)
            }

    # PersonDetectionRepository Implementation

    def save_person_detection(self, camera_id, filename, total_detections=0, max_people=0, avg_people=0.0, detections_json="", camera_name="", camera_location="", tenant_id="default") -> int:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO person_detections (camera_id, filename, total_detections, max_people, avg_people, detections_json, camera_name, camera_location, tenant_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (camera_id, filename, total_detections, max_people, avg_people, detections_json, camera_name, camera_location, tenant_id))
                return cursor.lastrowid

    def get_person_detections(self, limit=100, camera_id=None, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM person_detections WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_person_detection_stats(self, camera_id=None, tenant_id="default") -> Dict[str, Any]:
        with self._get_connection() as conn:
            query = "SELECT COUNT(*) as count, SUM(total_detections) as total, MAX(max_people) as peak FROM person_detections WHERE tenant_id = ?"
            params = [tenant_id]
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            row = conn.execute(query, params).fetchone()
            return {
                "total_videos": row['count'] or 0,
                "total_detections": row['total'] or 0,
                "peak_occupancy": row['peak'] or 0
            }

    # CameraRepository Implementation

    def save_camera(self, camera_id, name, location, ip, port=81, enabled=True, tenant_id="default") -> str:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("""
                    INSERT INTO cameras (id, name, location, ip, port, enabled, tenant_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id, tenant_id) DO UPDATE SET
                        name = excluded.name,
                        location = excluded.location,
                        ip = excluded.ip,
                        port = excluded.port,
                        enabled = excluded.enabled,
                        updated_at = CURRENT_TIMESTAMP
                """, (camera_id, name, location, ip, port, 1 if enabled else 0, tenant_id))
                return camera_id

    def get_camera(self, camera_id, tenant_id="default") -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM cameras WHERE id = ? AND tenant_id = ?", (camera_id, tenant_id)).fetchone()
            return dict(row) if row else None

    def list_cameras(self, tenant_id="default") -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM cameras WHERE tenant_id = ? ORDER BY created_at DESC", (tenant_id,)).fetchall()
            return [dict(r) for r in rows]

    def delete_camera(self, camera_id, tenant_id="default") -> bool:
        with self._get_connection() as conn:
            with self._get_cursor(conn) as cursor:
                cursor.execute("DELETE FROM cameras WHERE id = ? AND tenant_id = ?", (camera_id, tenant_id))
                return cursor.rowcount > 0

    # ProcessedFilesRepository Implementation

    def is_processed(self, filename: str, tenant_id: str = "default") -> bool:
        """Check if a file has already been processed."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT 1 FROM processed_files WHERE filename = ? AND tenant_id = ?", (filename, tenant_id)).fetchone()
            return row is not None

    def mark_processed(
        self,
        filename: str,
        camera_id: str,
        tenant_id: str = "default",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Mark a file as processed. Returns True if successfully marked (atomic)."""
        try:
            with self._get_connection() as conn:
                with self._get_cursor(conn) as cursor:
                    cursor.execute("""
                        INSERT OR IGNORE INTO processed_files (filename, camera_id, tenant_id, metadata_json)
                        VALUES (?, ?, ?, ?)
                    """, (filename, camera_id, tenant_id, json.dumps(metadata) if metadata else None))
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to mark file as processed: {e}")
            return False
