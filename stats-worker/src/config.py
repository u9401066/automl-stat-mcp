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

# Results storage (local directory for user-accessible results)
RESULTS_BASE_PATH = os.getenv("RESULTS_BASE_PATH", "/data/results")
