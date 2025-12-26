# =============================================================================
# Multi-Service Dockerfile
# =============================================================================
FROM python:3.11-slim AS base

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Fix permissions
RUN chown appuser:appuser /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Model Weights Stage
# =============================================================================
FROM base AS model-weights

# Download YOLO weights at build time
RUN pip install ultralytics==8.2.0
RUN mkdir -p /root/.cache/ultralytics && chown -R appuser:appuser /root/.cache/ultralytics

USER appuser
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Calculate checksums
USER root
RUN find /home/appuser/.cache/ultralytics -name "*.pt" -exec sha256sum {} \; > /weights.sha256

# =============================================================================
# ML Worker Service
# =============================================================================
FROM base AS ml-worker

# Copy code
COPY core/ core/
COPY infrastructure/ infrastructure/
COPY services/ services/
COPY ml_worker/ ml_worker/
COPY config/ config/

# Copy weights
COPY --from=model-weights /home/appuser/.cache/ultralytics /home/appuser/.cache/ultralytics
COPY --from=model-weights /weights.sha256 /app/weights.sha256

RUN chown -R appuser:appuser /app

USER appuser
# Validate checksums at build time and runtime entry
RUN cd / && sha256sum -c /app/weights.sha256

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "from ml_worker.database import get_connection; with get_connection(): pass"

CMD ["python", "ml_worker/consumer.py"]

# =============================================================================
# Event Dispatcher Service
# =============================================================================
FROM base AS dispatcher

COPY dispatcher/ /app/dispatcher/
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:5000/health

CMD ["python", "dispatcher/app.py"]

# =============================================================================
# Dashboard Service
# =============================================================================
FROM base AS dashboard

COPY core/ core/
COPY infrastructure/ infrastructure/
COPY ml_worker/ ml_worker/
COPY dashboard/ dashboard/
RUN chown -R appuser:appuser /app

USER appuser
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8501/_stcore/health

EXPOSE 8501
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501"]

# =============================================================================
# Camera API Service
# =============================================================================
FROM base AS camera-api

COPY core/ core/
COPY infrastructure/ infrastructure/
COPY camera_api/ camera_api/
RUN chown -R appuser:appuser /app

USER appuser
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health

EXPOSE 8000
CMD ["uvicorn", "camera_api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Test Stage
# =============================================================================
FROM base AS test

USER root
RUN pip install pytest pytest-cov flake8

COPY . .
RUN chown -R appuser:appuser /app

USER appuser
RUN flake8 --count --select=E9,F63,F7,F82 --show-source
RUN pytest tests/unit/ -v
