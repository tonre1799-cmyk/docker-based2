import os
import logging
import sentry_sdk
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import RESOURCE_ATTRIBUTES, Resource
from prometheus_client import start_http_server, Counter, Histogram, Gauge, Summary

logger = logging.getLogger(__name__)

def init_observability(service_name: str):
    """
    Initialize all observability components:
    1. Sentry (Error tracking)
    2. OpenTelemetry (Tracing)
    3. Prometheus (Metrics)
    """
    _init_sentry()
    _init_tracing(service_name)
    # Metrics server is typically started by the service itself if it needs a dedicated port,
    # or exposed via an endpoint (FastAPI/Flask).

def _init_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if dsn:
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("ENV", "development"),
            traces_sample_rate=1.0,
        )
        logger.info("Sentry initialized")
    else:
        logger.warning("SENTRY_DSN not set, Sentry integration disabled")

def _init_tracing(service_name: str):
    jaeger_host = os.getenv("JAEGER_HOST", "jaeger")
    jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))
    
    resource = Resource(attributes={
        RESOURCE_ATTRIBUTES.SERVICE_NAME: service_name
    })
    
    provider = TracerProvider(resource=resource)
    
    try:
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )
        processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info(f"OpenTelemetry tracing initialized for {service_name} (Jaeger: {jaeger_host}:{jaeger_port})")
    except Exception as e:
        logger.error(f"Failed to initialize Jaeger exporter: {e}")

def get_tracer(name: str):
    return trace.get_tracer(name)

# Centralized Metrics
VIDEOS_PROCESSED = Counter(
    'videos_processed_total',
    'Total videos processed',
    ['camera_id', 'status', 'model']
)

PROCESSING_DURATION = Histogram(
    'video_processing_seconds',
    'Video processing duration',
    ['model'],
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

VIDEO_SIZE = Histogram(
    'video_size_bytes',
    'Video file size',
    buckets=[1e6, 5e6, 10e6, 50e6, 100e6]
)

QUEUE_DEPTH = Gauge('queue_depth', 'Redis queue depth')

MODEL_INFERENCE_TIME = Summary(
    'model_inference_seconds',
    'Model inference time',
    ['model', 'camera_id']
)
