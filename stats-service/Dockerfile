# =============================================================================
# Stats Service Dockerfile
# =============================================================================
# Lightweight API service for statistical analysis job submission
# Actual processing done by stats-worker
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Configure apt to use HTTPS
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null || true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV SERVICE_HOST=0.0.0.0
ENV SERVICE_PORT=8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"]
