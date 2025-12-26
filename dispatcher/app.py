"""
Event Dispatcher Service
=========================
Receives webhooks from Kerberos Vault and pushes tasks to Redis queue.
Enables horizontal scaling of ML workers.
"""

import json
import os
import logging
import jwt
from functools import wraps
from flask import Flask, request, jsonify, abort
from pydantic import BaseModel, ValidationError, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
import sys # Added for sys.exit()

from core.observability import init_observability, get_tracer
from core.logging_setup import setup_logging
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from prometheus_client import make_flask_app, Counter

# Initialize structured logging
logger = setup_logging()

import redis
from core.config_manager import get_config

# Load configuration
config = get_config()

# Security Check: Enforce strong SECRET_KEY
if not config.secret_key or config.secret_key == "super-secret-key-change-it":
    logger.critical("❌ CRITICAL: SECRET_KEY is missing or set to default value!")
    logger.critical("Please set a strong SECRET_KEY (min 32 characters) in your .env file.")
    sys.exit(1)
if len(config.secret_key) < 32:
    logger.warning("⚠️ WARNING: SECRET_KEY is shorter than 32 characters. Consider using a stronger key.")

# Initialize Redis connection pool
redis_pool = redis.ConnectionPool(
    host=config.redis_host, 
    port=config.redis_port, 
    decode_responses=True,
    max_connections=20
)
redis_client = redis.Redis(connection_pool=redis_pool)

# Security Check: Enforce strong SECRET_KEY
raw_secret = config.secret_key.get_secret_value()
if not raw_secret or raw_secret == "super-secret-key-change-it":
    logger.critical("❌ CRITICAL: SECRET_KEY is missing or set to default value!")
    sys.exit(1)
if len(raw_secret) < 32:
    logger.critical("❌ CRITICAL: SECRET_KEY is too weak (min 32 characters required).")
    sys.exit(1)

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = Flask(__name__)
app.state = type('State', (), {'limiter': limiter})() 
FlaskInstrumentor().instrument_app(app)

# Pydantic Model for Webhook
class WebhookPayload(BaseModel):
    camera_id: str = Field(alias='cameraId', default="unknown")
    tenant_id: str = "default"
    filename: str
    s3_key: str = Field(alias='key', default="")
    timestamp: int = 0
    bucket: str = "recordings"

    class Config:
        populate_by_name = True

# Prometheus metrics
WEBHOOK_RECEIVED = Counter('webhook_received_total', 'Total webhooks received', ['status'])

# Add /metrics endpoint
app.wsgi_app = make_flask_app(app.wsgi_app)

TASK_QUEUE = config.task_queue

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            # Enforce expiration check (leverage PyJWT default behavior)
            payload = jwt.decode(token, config.secret_key.get_secret_value(), algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    return decorated


@app.route("/health", methods=["GET"])
@limiter.limit("10/minute")
def health():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "service": "dispatcher",
        "dependencies": {
            "redis": "connected"
        }
    }
    try:
        redis_client.ping()
        return jsonify(health_status), 200
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["dependencies"]["redis"] = f"disconnected: {str(e)}"
        return jsonify(health_status), 500


@app.route("/webhook", methods=["POST"])
@limiter.limit("100/minute")
@requires_auth
def webhook():
    """
    Receive webhook from Kerberos Vault when a new recording is saved.
    Push task to Redis queue for ML workers to process.
    """
    try:
        # Validate and parse payload
        try:
            data = WebhookPayload(**request.json)
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return jsonify({"status": "error", "message": e.errors()}), 400
            
        logger.info(f"Received webhook: {data.filename} for tenant {request.user.get('tenant_id')}")
        
        tenant_id = request.user.get("tenant_id", "default")
        
        # Build task from validated data
        task = data.dict()
        task["tenant_id"] = tenant_id # Override with authenticated tenant_id
        
        # Guard: Check queue size to prevent OOM/Infinite growth
        queue_size = redis_client.llen(TASK_QUEUE)
        if queue_size > 10000: # Configuration-based threshold would be better
            logger.warning(f"Queue size exceeded threshold ({queue_size}). Rejecting task.")
            return jsonify({"status": "error", "message": "Dispatcher busy, queue full"}), 503

        # Push to Redis queue
        with tracer.start_as_current_span("queue_task") as span:
            span.set_attribute("filename", task["filename"])
            redis_client.rpush(TASK_QUEUE, json.dumps(task))
        
        WEBHOOK_RECEIVED.labels(status='success').inc()
        return jsonify({"status": "queued", "task": {"filename": data.filename}}), 200
        
    except Exception as e:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
        logger.error(f"Error processing webhook: {e}")
        WEBHOOK_RECEIVED.labels(status='error').inc()
        return jsonify({"status": "error", "message": "Internal error"}), 500


@app.route("/queue/stats", methods=["GET"])
@limiter.limit("10/minute")
@requires_auth
def queue_stats():
    """Get detailed queue statistics."""
    try:
        pending = redis_client.llen(TASK_QUEUE)
        # Attempt to get DLQ length if it exists
        dlq = 0
        try:
            dlq = redis_client.llen(f"{TASK_QUEUE}_dlq")
        except:
            pass
            
        return jsonify({
            "status": "success",
            "queue": {
                "name": TASK_QUEUE,
                "pending_tasks": pending,
                "dlq_tasks": dlq
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("  Event Dispatcher Started")
    logger.info("=" * 50)
    logger.info(f"Redis: {config.redis_host}:{config.redis_port}")
    logger.info(f"Queue: {config.task_queue}")
    
    import signal
    import sys

    def signal_handler(sig, frame):
        logger.info("Shutting down Dispatcher...")
        try:
            redis_client.close()
        except:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app.run(host="0.0.0.0", port=5000, debug=False)
