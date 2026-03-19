"""
Domain Events - Events raised by domain entities
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict


@dataclass(frozen=True)
class DomainEvent:
    """Base class for domain events"""

    occurred_at: datetime


@dataclass(frozen=True)
class DatasetRegistered(DomainEvent):
    """Event raised when a new dataset is registered"""

    dataset_id: str
    user_id: str
    name: str
    minio_path: str


@dataclass(frozen=True)
class JobCreated(DomainEvent):
    """Event raised when a new training job is created"""

    job_id: str
    user_id: str
    job_type: str
    dataset_id: str


@dataclass(frozen=True)
class JobStarted(DomainEvent):
    """Event raised when a job starts running"""

    job_id: str


@dataclass(frozen=True)
class JobProgressUpdated(DomainEvent):
    """Event raised when job progress is updated"""

    job_id: str
    progress: float
    message: str


@dataclass(frozen=True)
class JobCompleted(DomainEvent):
    """Event raised when a job completes successfully"""

    job_id: str
    model_id: str
    result: Dict[str, Any]


@dataclass(frozen=True)
class JobFailed(DomainEvent):
    """Event raised when a job fails"""

    job_id: str
    error_message: str


@dataclass(frozen=True)
class ModelTrained(DomainEvent):
    """Event raised when a model is trained"""

    model_id: str
    user_id: str
    best_score: float
    best_model_name: str
