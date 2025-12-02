"""
Job - Aggregate Root for async training jobs
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of training job"""
    AUTOML = "automl"           # Full AutoML search
    SPECIFIC = "specific"       # Specific algorithm(s)
    COMPARE = "compare"         # Compare multiple algorithms


@dataclass(frozen=True)
class JobId:
    """Value Object for Job identifier"""
    value: UUID

    @classmethod
    def generate(cls) -> "JobId":
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "JobId":
        return cls(value=UUID(id_str))

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Job:
    """
    Job Aggregate Root
    
    Represents an async training job.
    """
    id: JobId
    job_type: JobType
    user_id: str
    dataset_id: str
    
    # Status
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    status_message: str = ""
    
    # Configuration (stored as dict for flexibility)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Results
    model_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def start(self) -> None:
        """Mark job as started"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.status_message = "Training started"

    def update_progress(self, progress: float, message: str = "") -> None:
        """Update job progress"""
        self.progress = min(max(progress, 0.0), 1.0)
        if message:
            self.status_message = message

    def complete(self, model_id: str, result: Dict[str, Any]) -> None:
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.progress = 1.0
        self.model_id = model_id
        self.result = result
        self.completed_at = datetime.utcnow()
        self.status_message = "Training completed successfully"

    def fail(self, error_message: str) -> None:
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.status_message = f"Training failed: {error_message}"

    def cancel(self) -> None:
        """Mark job as cancelled"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        self.status_message = "Training cancelled by user"

    def is_terminal(self) -> bool:
        """Check if job is in terminal state"""
        return self.status in (
            JobStatus.COMPLETED, 
            JobStatus.FAILED, 
            JobStatus.CANCELLED
        )

    def belongs_to(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Check if job belongs to user/session"""
        if self.user_id != user_id:
            return False
        if session_id and self.session_id and self.session_id != session_id:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "job_id": str(self.id),
            "job_type": self.job_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "status_message": self.status_message,
            "model_id": self.model_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
