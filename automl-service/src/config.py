"""
Configuration settings for AutoML Service
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
JOBS_DIR = BASE_DIR / "jobs"

# Create directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "automl-datasets")

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
