"""
Stats Service Configuration
"""
import os

# Service settings
SERVICE_HOST = os.getenv("SERVICE_HOST", "0.0.0.0")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8003"))

# Redis settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Redis key prefixes (separate from automl)
STATS_JOBS_PENDING = "stats:jobs:pending"
STATS_JOBS_PREFIX = "stats:jobs:"

# MinIO settings
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_DATASET_BUCKET = os.getenv("MINIO_DATASET_BUCKET", "automl-datasets")
MINIO_REPORTS_BUCKET = os.getenv("MINIO_REPORTS_BUCKET", "stats-reports")

# Job settings
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "3600"))  # 1 hour default
