# =============================================================================
# AutoGluon Worker Dockerfile
# =============================================================================
#
# Uses official AutoGluon base image. Only add minimal wrapper code.
# When AutoGluon updates, just change the FROM tag.
#
# Available tags: https://hub.docker.com/r/autogluon/autogluon/tags
# =============================================================================

# ============ CHANGE THIS TAG TO UPDATE AUTOGLUON ============
FROM autogluon/autogluon:1.2.0-cpu-py3.10
# For GPU: autogluon/autogluon:1.2.0-cuda11.8-py3.10
# =============================================================

WORKDIR /app

# Only install worker dependencies (API service handles the rest)
RUN pip install --no-cache-dir \
    redis>=5.0.0 \
    minio>=7.2.0 \
    httpx>=0.25.0

# Copy only the worker code
COPY src/infrastructure/autogluon/ ./worker/
COPY src/domain/models/ ./domain/models/

# Worker temp directory (models are saved to MinIO, not kept locally)
RUN mkdir -p /tmp/autogluon-work

ENV PYTHONPATH=/app
ENV WORKER_TEMP_DIR=/tmp/autogluon-work

# Run the worker process
CMD ["python", "-m", "worker.worker"]
