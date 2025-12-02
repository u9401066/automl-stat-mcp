# =============================================================================
# AutoML API Service Dockerfile (Lightweight - No AutoGluon)
# =============================================================================
#
# This container only handles:
# - REST API endpoints
# - Job queue management (Redis)
# - Communication with AutoGluon worker container
# - MinIO file operations (streaming, no local storage)
#
# AutoGluon runs in a SEPARATE container (automl-worker).
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Minimal system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# No local data storage - everything goes to MinIO
# Only keep a small temp directory for streaming
RUN mkdir -p /tmp/automl-temp

ENV PYTHONPATH=/app
ENV API_HOST=0.0.0.0
ENV API_PORT=8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
