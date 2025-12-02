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
FROM autogluon/autogluon:1.3.1-cpu-framework-ubuntu22.04-py3.11
# For GPU: autogluon/autogluon:1.3.1-cuda12.4-framework-ubuntu22.04-py3.11
# =============================================================

WORKDIR /app

# Install additional worker dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the worker code
COPY src/ ./src/

# Worker temp directory (models are saved to MinIO, not kept locally)
RUN mkdir -p /tmp/autogluon-work

ENV PYTHONPATH=/app
ENV WORKER_TEMP_DIR=/tmp/autogluon-work

# Run the worker process
CMD ["python", "-m", "src.worker"]
