"""
Data Transfer Objects for Stats Service
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ============== Request DTOs ==============

@dataclass
class SubmitAutoAnalyzeRequest:
    """Request for auto-analyze job submission"""
    dataset_id: str
    user_id: str
    session_id: Optional[str] = None
    target_column: Optional[str] = None


@dataclass
class SubmitDirectAnalyzeRequest:
    """Request for direct CSV analysis (no MinIO)"""
    csv_content: str
    user_id: str
    is_base64: bool = False
    target_column: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class SubmitEDARequest:
    """Request for EDA job submission"""
    dataset_id: str
    user_id: str
    session_id: Optional[str] = None
    title: str = "EDA Report"
    minimal: bool = True


@dataclass
class SubmitTableOneRequest:
    """Request for TableOne job submission"""
    dataset_id: str
    user_id: str
    session_id: Optional[str] = None
    columns: Optional[List[str]] = None
    categorical: Optional[List[str]] = None
    continuous: Optional[List[str]] = None
    groupby: Optional[str] = None
    nonnormal: Optional[List[str]] = None
    pval: bool = False


# ============== Response DTOs ==============

@dataclass
class StatsJobResponse:
    """Response for stats job"""
    job_id: str
    job_type: str
    status: str
    progress: float
    message: str
    result_path: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class DataPreviewResponse:
    """Response for data preview"""
    rows: int
    columns: int
    column_names: List[str]
    dtypes: Dict[str, str]
    sample_rows: List[Dict[str, Any]]
