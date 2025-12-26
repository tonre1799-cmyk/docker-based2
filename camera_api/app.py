"""
Camera Management API
=====================
REST API for managing cameras and their configuration.
Replaces manual YAML edits with a programmatic interface.
"""

from fastapi import FastAPI, HTTPException, Request, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import psycopg2.extras
import os
import json
import jwt
from core.logging_setup import setup_logging
from core.observability import init_observability, get_tracer
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize structured logging
logger = setup_logging()

# Initialize Observability
init_observability("camera-api")
tracer = get_tracer(__name__)

app = FastAPI(title="Camera Management API")
FastAPIInstrumentor.instrument_app(app)

# Add /metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# PostgreSQL configuration
PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
PG_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
PG_DATABASE = os.environ.get("POSTGRES_DB", "analytics")
PG_USER = os.environ.get("POSTGRES_USER", "analytics_user")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "analytics_pass")
SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-key-change-it")

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


class Camera(BaseModel):
    """Camera model."""
    id: str
    name: str
    location: str
    ip: str
    port: int = 81
    enabled: bool = True


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DATABASE,
        user=PG_USER,
        password=PG_PASSWORD
    )


def init_camera_table():
    """Initialize cameras table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id TEXT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            name TEXT NOT NULL,
            location TEXT NOT NULL,
            ip TEXT NOT NULL,
            port INTEGER DEFAULT 81,
            enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (id, tenant_id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cameras_tenant ON cameras(tenant_id)")
    
    conn.commit()
    conn.close()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing Camera Management API...")
    init_camera_table()
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Camera Management API...")
    # SQL connections are short-lived via context manager, nothing to close globally.


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Camera Management API", "version": "1.0.0"}


@app.get("/cameras", response_model=List[Camera])
def list_cameras(user=Depends(verify_token)):
    """Get all cameras for current tenant."""
    tenant_id = user.get("tenant_id", "default")
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("SELECT id, name, location, ip, port, enabled FROM cameras WHERE tenant_id = %s ORDER BY created_at DESC", (tenant_id,))
    cameras = cursor.fetchall()
    
    conn.close()
    return [dict(cam) for cam in cameras]


@app.get("/cameras/{camera_id}", response_model=Camera)
def get_camera(camera_id: str, user=Depends(verify_token)):
    """Get a specific camera by ID for current tenant."""
    tenant_id = user.get("tenant_id", "default")
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cursor.execute("SELECT id, name, location, ip, port, enabled FROM cameras WHERE id = %s AND tenant_id = %s", (camera_id, tenant_id))
    camera = cursor.fetchone()
    
    conn.close()
    
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return dict(camera)


@app.post("/cameras", response_model=Camera, status_code=201)
@limiter.limit("10/minute")
def create_camera(camera: Camera, request: Request, user=Depends(verify_token)):
    """Create a new camera for current tenant."""
    tenant_id = user.get("tenant_id", "default")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO cameras (id, name, location, ip, port, enabled, tenant_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (camera.id, camera.name, camera.location, camera.ip, camera.port, camera.enabled, tenant_id))
        
        conn.commit()
        logger.info(f"Created camera: {camera.id} for tenant {tenant_id}")
    except psycopg2.IntegrityError:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=400, detail="Camera with this ID already exists for this tenant")
    finally:
        conn.close()
    
    return camera


@app.put("/cameras/{camera_id}", response_model=Camera)
def update_camera(camera_id: str, camera: Camera, user=Depends(verify_token)):
    """Update an existing camera for current tenant."""
    tenant_id = user.get("tenant_id", "default")
    if camera_id != camera.id:
        raise HTTPException(status_code=400, detail="Camera ID mismatch")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE cameras
        SET name = %s, location = %s, ip = %s, port = %s, enabled = %s, updated_at = NOW()
        WHERE id = %s AND tenant_id = %s
    """, (camera.name, camera.location, camera.ip, camera.port, camera.enabled, camera_id, tenant_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Updated camera: {camera_id} for tenant {tenant_id}")
    return camera


@app.delete("/cameras/{camera_id}")
def delete_camera(camera_id: str, user=Depends(verify_token)):
    """Delete a camera for current tenant."""
    tenant_id = user.get("tenant_id", "default")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM cameras WHERE id = %s AND tenant_id = %s", (camera_id, tenant_id))
    
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Camera not found or access denied")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Deleted camera: {camera_id} for tenant {tenant_id}")
    return {"message": f"Camera {camera_id} deleted successfully"}


@app.get("/health")
def health():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "service": "camera-api",
        "dependencies": {
            "database": "connected"
        }
    }
    try:
        conn = get_db_connection()
        conn.close()
        return health_status
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["dependencies"]["database"] = f"disconnected: {str(e)}"
        from fastapi import Response
        return Response(content=json.dumps(health_status), status_code=500, media_type="application/json")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
