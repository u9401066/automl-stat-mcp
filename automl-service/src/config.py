"""
Configuration settings for AutoML Service

Note: All storage is on MinIO, no local file storage.
      Metadata persistence uses PERSIST_DIR environment variable (see repositories.py)
"""
import os

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "automl-datasets")

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# AutoGluon Configuration
AUTOGLUON_PRESETS = os.getenv("AUTOGLUON_PRESETS", "medium_quality")
DEFAULT_TIME_LIMIT = int(os.getenv("DEFAULT_TIME_LIMIT", "300"))  # 5 minutes

# Available algorithms in AutoGluon
AVAILABLE_ALGORITHMS = {
    "GBM": "LightGBM",
    "CAT": "CatBoost",
    "XGB": "XGBoost",
    "RF": "Random Forest",
    "XT": "Extremely Randomized Trees",
    "KNN": "K-Nearest Neighbors",
    "LR": "Linear Model",
    "NN_TORCH": "Neural Network (PyTorch)",
    "FASTAI": "FastAI Neural Network",
}

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8001"))
