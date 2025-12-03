# Stats Worker Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Environment variables (defaults)
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    MINIO_ENDPOINT=minio:9000 \
    MINIO_ACCESS_KEY=minioadmin \
    MINIO_SECRET_KEY=minioadmin \
    MINIO_SECURE=false

# Run worker
CMD ["python", "-m", "src.worker"]
