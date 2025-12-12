"""
Stats Worker Configuration
"""
import os

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Redis key prefixes
STATS_JOBS_PENDING = "stats:jobs:pending"
STATS_JOBS_PREFIX = "stats:jobs:"

# MinIO settings
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_DATASET_BUCKET = os.getenv("MINIO_DATASET_BUCKET", "automl-datasets")
MINIO_REPORTS_BUCKET = os.getenv("MINIO_REPORTS_BUCKET", "stats-reports")

# Worker settings
WORKER_POLL_INTERVAL = int(os.getenv("WORKER_POLL_INTERVAL", "1"))
TEMP_DIR = os.getenv("WORKER_TEMP_DIR", "/tmp/stats-work")

# Redis TTL settings (seconds)
# Job results expire after 24 hours - use MinIO for permanent storage
REDIS_JOB_TTL = int(os.getenv("REDIS_JOB_TTL", str(24 * 60 * 60)))  # 24 hours
REDIS_TEMP_DATA_TTL = int(os.getenv("REDIS_TEMP_DATA_TTL", str(1 * 60 * 60)))  # 1 hour
