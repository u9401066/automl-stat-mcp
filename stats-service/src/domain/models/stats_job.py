"""
StatsJob - Aggregate Root for statistical analysis jobs
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


class StatsJobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StatsJobType(str, Enum):
    """Type of statistics job"""
    EDA = "eda"                           # ydata-profiling EDA report
    TABLEONE = "tableone"                 # TableOne summary statistics
    AUTO_ANALYZE = "auto_analyze"         # Intelligent auto analysis
    AUTO_ANALYZE_DIRECT = "auto_analyze_direct"  # Direct CSV analysis
    # Propensity Score Analysis
    PROPENSITY_ESTIMATE = "propensity_estimate"
    PROPENSITY_MATCH = "propensity_match"
    PROPENSITY_EFFECT = "propensity_effect"
    PROPENSITY_FULL = "propensity_full"
    # Survival Analysis
    KAPLAN_MEIER = "kaplan_meier"
    COX_PH = "cox_ph"
    COX_REGRESSION = "cox_regression"
    SURVIVAL_COMPARISON = "survival_comparison"
    SURVIVAL_COMPARE = "survival_compare"
    SURVIVAL_SUMMARY = "survival_summary"
    # ROC Analysis
    ROC = "roc"
    ROC_COMPUTE = "roc_compute"
    ROC_COMPARE = "roc_compare"
    ROC_COMPARE_MULTIPLE = "roc_compare_multiple"
    ROC_THRESHOLD = "roc_threshold"
    ROC_CALIBRATION = "roc_calibration"
    ROC_FULL_EVAL = "roc_full_eval"
    # Power Analysis
    POWER = "power"


@dataclass(frozen=True)
class StatsJobId:
    """Value Object for StatsJob identifier"""
    value: str  # Changed from UUID to str to support various ID formats

    @classmethod
    def generate(cls) -> "StatsJobId":
        return cls(value=str(uuid4()))

    @classmethod
    def from_string(cls, id_str: str) -> "StatsJobId":
        return cls(value=id_str)

    def __str__(self) -> str:
        return self.value


@dataclass
class StatsJob:
    """
    StatsJob Aggregate Root

    Represents an async statistical analysis job.
    """
    id: StatsJobId
    job_type: StatsJobType
    user_id: str

    # Optional references
    dataset_id: Optional[str] = None  # Reference to dataset (if not direct)
    minio_path: Optional[str] = None  # CSV path in MinIO

    # Status
    status: StatsJobStatus = StatsJobStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""

    # Configuration (job-specific params)
    params: Dict[str, Any] = field(default_factory=dict)

    # Results
    result_path: Optional[str] = None  # Path to result in MinIO
    result: Optional[Dict[str, Any]] = None  # Result data (for small results)
    error: Optional[str] = None

    # Metadata
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ============== Domain Methods ==============

    def start(self) -> None:
        """Mark job as started"""
        if self.status != StatsJobStatus.PENDING:
            raise ValueError(f"Cannot start job in status {self.status}")

        self.status = StatsJobStatus.RUNNING
        self.started_at = datetime.utcnow()
        self.message = f"{self.job_type.value} analysis started"

    def update_progress(self, progress: float, message: str = "") -> None:
        """Update job progress"""
        if self.status != StatsJobStatus.RUNNING:
            return

        self.progress = min(1.0, max(0.0, progress))
        if message:
            self.message = message

    def complete(
        self,
        result_path: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mark job as completed"""
        self.status = StatsJobStatus.COMPLETED
        self.progress = 1.0
        self.completed_at = datetime.utcnow()
        self.result_path = result_path
        self.result = result
        self.message = f"{self.job_type.value} analysis completed"

    def fail(self, error: str) -> None:
        """Mark job as failed"""
        self.status = StatsJobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error = error
        self.message = f"Analysis failed: {error}"

    def belongs_to(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Check if job belongs to user/session"""
        if self.user_id != user_id:
            return False
        if session_id and self.session_id and self.session_id != session_id:
            return False
        return True

    def is_pending(self) -> bool:
        return self.status == StatsJobStatus.PENDING

    def is_running(self) -> bool:
        return self.status == StatsJobStatus.RUNNING

    def is_completed(self) -> bool:
        return self.status == StatsJobStatus.COMPLETED

    def is_failed(self) -> bool:
        return self.status == StatsJobStatus.FAILED

    def is_done(self) -> bool:
        """Check if job is in terminal state"""
        return self.status in (StatsJobStatus.COMPLETED, StatsJobStatus.FAILED)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "job_id": str(self.id),
            "job_type": self.job_type.value,
            "user_id": self.user_id,
            "dataset_id": self.dataset_id,
            "minio_path": self.minio_path,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "params": self.params,
            "result_path": self.result_path,
            "result": self.result,
            "error": self.error,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatsJob":
        """Create from dictionary"""
        from datetime import datetime as dt

        def parse_datetime(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            return dt.fromisoformat(s)

        return cls(
            id=StatsJobId.from_string(data["job_id"]),
            job_type=StatsJobType(data["job_type"]),
            user_id=data["user_id"],
            dataset_id=data.get("dataset_id"),
            minio_path=data.get("minio_path"),
            status=StatsJobStatus(data.get("status", "pending")),
            progress=float(data.get("progress", 0.0)),
            message=data.get("message", ""),
            params=data.get("params", {}),
            result_path=data.get("result_path"),
            result=data.get("result"),
            error=data.get("error"),
            session_id=data.get("session_id"),
            created_at=parse_datetime(data.get("created_at")) or datetime.utcnow(),
            started_at=parse_datetime(data.get("started_at")),
            completed_at=parse_datetime(data.get("completed_at")),
        )
