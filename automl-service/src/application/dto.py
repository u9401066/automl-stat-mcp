"""
DTOs - Data Transfer Objects for Application Layer
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ============== Request DTOs ==============


@dataclass
class RegisterDatasetRequest:
    """Request to register a dataset from MinIO"""

    name: str
    minio_path: str
    user_id: str
    session_id: Optional[str] = None
    description: Optional[str] = None


@dataclass
class AutoMLTrainRequest:
    """Request for AutoML training"""

    dataset_id: str
    target_column: str
    problem_type: str  # "binary", "multiclass", "regression"
    user_id: str
    session_id: Optional[str] = None
    time_limit: int = 300
    presets: str = "medium_quality"
    metric: Optional[str] = None


@dataclass
class SpecificTrainRequest:
    """Request for training with specific algorithms"""

    dataset_id: str
    target_column: str
    problem_type: str
    algorithms: List[str]  # e.g., ["XGB", "GBM", "RF"]
    user_id: str
    session_id: Optional[str] = None
    time_limit: int = 300
    hyperparameters: Optional[Dict[str, Any]] = None


@dataclass
class CompareModelsRequest:
    """Request to compare multiple algorithms"""

    dataset_id: str
    target_column: str
    problem_type: str
    algorithms: List[str]
    user_id: str
    session_id: Optional[str] = None
    time_limit: int = 300


@dataclass
class PredictRequest:
    """Request for prediction"""

    model_id: str
    dataset_id: str
    user_id: str


# ============== Response DTOs ==============


@dataclass
class DatasetResponse:
    """Response containing dataset info"""

    dataset_id: str
    name: str
    minio_path: str
    columns: List[str]
    row_count: int
    file_size_bytes: int
    created_at: str
    description: Optional[str] = None


@dataclass
class JobResponse:
    """Response containing job info"""

    job_id: str
    job_type: str
    status: str
    progress: float
    status_message: str
    model_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class LeaderboardEntryResponse:
    """Single entry in model leaderboard"""

    model_name: str
    score: float
    fit_time: float
    pred_time: float
    stack_level: int = 0


@dataclass
class ModelResponse:
    """Response containing model info"""

    model_id: str
    name: str
    problem_type: str
    target_column: str
    best_model_name: str
    best_score: float
    metric: str
    algorithms_used: List[str]
    leaderboard: List[LeaderboardEntryResponse] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class PredictResponse:
    """Response containing predictions"""

    model_id: str
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None


@dataclass
class ErrorResponse:
    """Error response"""

    error: str
    detail: Optional[str] = None
