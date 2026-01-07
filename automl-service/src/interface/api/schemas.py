"""
Pydantic API Schemas for FastAPI
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============== Request Schemas ==============

class RegisterDatasetRequest(BaseModel):
    """Request to register a dataset from MinIO"""
    name: str = Field(..., description="Dataset name")
    minio_path: str = Field(..., description="Path to file in MinIO (e.g., bucket/path/file.csv)")
    description: Optional[str] = Field(None, description="Dataset description")


class UploadDatasetRequest(BaseModel):
    """Request to upload CSV content directly"""
    name: str = Field(..., description="Dataset name")
    csv_content: str = Field(..., description="CSV content as string")
    description: Optional[str] = Field(None, description="Dataset description")


class AutoMLTrainRequest(BaseModel):
    """Request for AutoML training"""
    dataset_id: str = Field(..., description="Dataset ID")
    target_column: str = Field(..., description="Target column name")
    problem_type: str = Field(..., description="Problem type: binary, multiclass, or regression")
    time_limit: int = Field(300, description="Time limit in seconds")
    presets: str = Field("medium_quality", description="AutoGluon presets")
    metric: Optional[str] = Field(None, description="Evaluation metric (auto-selected if not specified)")


class SpecificTrainRequest(BaseModel):
    """Request for training with specific algorithms"""
    dataset_id: str = Field(..., description="Dataset ID")
    target_column: str = Field(..., description="Target column name")
    problem_type: str = Field(..., description="Problem type: binary, multiclass, or regression")
    algorithms: List[str] = Field(..., description="Algorithms to use (e.g., ['XGB', 'GBM', 'RF'])")
    time_limit: int = Field(300, description="Time limit in seconds")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Custom hyperparameters")


class CompareModelsRequest(BaseModel):
    """Request to compare multiple algorithms"""
    dataset_id: str = Field(..., description="Dataset ID")
    target_column: str = Field(..., description="Target column name")
    problem_type: str = Field(..., description="Problem type: binary, multiclass, or regression")
    algorithms: List[str] = Field(..., description="Algorithms to compare (minimum 2)")
    time_limit: int = Field(300, description="Time limit in seconds")


class PredictRequest(BaseModel):
    """Request for prediction"""
    model_id: str = Field(..., description="Model ID")
    dataset_id: str = Field(..., description="Dataset ID for prediction data")


# ============== Response Schemas ==============

class DatasetResponse(BaseModel):
    """Response containing dataset info"""
    dataset_id: str
    name: str
    minio_path: str
    columns: List[str]
    row_count: int
    file_size_bytes: int
    created_at: str
    description: Optional[str] = None


class JobResponse(BaseModel):
    """Response containing job info"""
    job_id: str
    job_type: str
    status: str
    progress: float
    status_message: str
    model_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class JobListResponse(BaseModel):
    """Response containing list of jobs"""
    jobs: List[JobResponse]
    total: int


class LeaderboardEntryResponse(BaseModel):
    """Single entry in model leaderboard"""
    model_name: str
    score: float
    fit_time: float
    pred_time: float
    stack_level: int = 0


class ModelResponse(BaseModel):
    """Response containing model info"""
    model_id: str
    name: str
    problem_type: str
    target_column: str
    best_model_name: str
    best_score: float
    metric: str
    algorithms_used: List[str]
    leaderboard: List[LeaderboardEntryResponse] = []
    feature_importance: Dict[str, float] = {}
    created_at: str


class PredictResponse(BaseModel):
    """Response containing predictions"""
    model_id: str
    predictions: List[Any]
    probabilities: Optional[List[List[float]]] = None


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
