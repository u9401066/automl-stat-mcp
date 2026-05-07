"""
In-Memory Repository Implementations

Metadata is persisted to local JSON files for restart recovery.
Actual data/models are stored in MinIO.

For production, consider using Redis or PostgreSQL for metadata.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..domain.models import (
    Dataset,
    DatasetId,
    Job,
    JobId,
    JobStatus,
    JobType,
    LeaderboardEntry,
    MLModel,
    ModelId,
)
from ..domain.repositories import DatasetRepository, JobRepository, ModelRepository
from .redis_dataset_store import redis_dataset_store

# Persistence directories - configurable via environment variable
PERSIST_DIR = Path(os.environ.get("PERSIST_DIR", "/app/data"))
DATASETS_META_DIR = PERSIST_DIR / "datasets"
MODELS_META_DIR = PERSIST_DIR / "models"
JOBS_META_DIR = PERSIST_DIR / "jobs"

# Ensure directories exist
DATASETS_META_DIR.mkdir(parents=True, exist_ok=True)
MODELS_META_DIR.mkdir(parents=True, exist_ok=True)
JOBS_META_DIR.mkdir(parents=True, exist_ok=True)


class InMemoryDatasetRepository(DatasetRepository):
    """In-memory implementation of DatasetRepository with JSON persistence"""

    def __init__(self):
        self._datasets: Dict[str, Dataset] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load datasets from disk on startup"""
        if DATASETS_META_DIR.exists():
            for meta_file in DATASETS_META_DIR.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        dataset = Dataset(
                            id=DatasetId.from_string(data["id"]),
                            name=data["name"],
                            minio_path=data["minio_path"],
                            user_id=data["user_id"],
                            session_id=data.get("session_id"),
                            description=data.get("description"),
                            columns=data.get("columns", []),
                            row_count=data.get("row_count", 0),
                            file_size_bytes=data.get("file_size_bytes", 0),
                            created_at=datetime.fromisoformat(data["created_at"]),
                        )
                        self._datasets[str(dataset.id)] = dataset
                except Exception:
                    pass

    def _save_to_disk(self, dataset: Dataset):
        """Persist dataset metadata to disk"""
        meta_file = DATASETS_META_DIR / f"{dataset.id}.json"
        data = {
            "id": str(dataset.id),
            "name": dataset.name,
            "minio_path": dataset.minio_path,
            "user_id": dataset.user_id,
            "session_id": dataset.session_id,
            "description": dataset.description,
            "columns": dataset.columns,
            "row_count": dataset.row_count,
            "file_size_bytes": dataset.file_size_bytes,
            "created_at": dataset.created_at.isoformat(),
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_to_redis(self, dataset: Dataset):
        """Save dataset metadata to Redis for cross-service access"""
        redis_dataset_store.save_dataset({
            "dataset_id": str(dataset.id),
            "name": dataset.name,
            "minio_path": dataset.minio_path,
            "user_id": dataset.user_id,
            "session_id": dataset.session_id,
            "description": dataset.description,
            "columns": dataset.columns,
            "row_count": dataset.row_count,
            "file_size_bytes": dataset.file_size_bytes,
            "created_at": dataset.created_at.isoformat(),
        })

    async def save(self, dataset: Dataset) -> None:
        self._datasets[str(dataset.id)] = dataset
        self._save_to_disk(dataset)
        self._save_to_redis(dataset)  # Sync to Redis for stats-service

    async def get_by_id(self, dataset_id: DatasetId) -> Optional[Dataset]:
        return self._datasets.get(str(dataset_id))

    async def find_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[Dataset]:
        return [
            ds for ds in self._datasets.values()
            if ds.belongs_to(user_id, session_id)
        ]

    async def delete(self, dataset_id: DatasetId) -> bool:
        key = str(dataset_id)
        if key in self._datasets:
            user_id = self._datasets[key].user_id
            del self._datasets[key]
            meta_file = DATASETS_META_DIR / f"{key}.json"
            if meta_file.exists():
                meta_file.unlink()
            # Also delete from Redis
            redis_dataset_store.delete_dataset(key, user_id)
            return True
        return False

    async def exists(self, dataset_id: DatasetId) -> bool:
        return str(dataset_id) in self._datasets


class InMemoryModelRepository(ModelRepository):
    """In-memory implementation of ModelRepository"""

    def __init__(self):
        self._models: Dict[str, MLModel] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load models from disk on startup"""
        if MODELS_META_DIR.exists():
            for meta_file in MODELS_META_DIR.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        leaderboard = [
                            LeaderboardEntry(**entry)
                            for entry in data.get("leaderboard", [])
                        ]
                        model = MLModel(
                            id=ModelId.from_string(data["id"]),
                            name=data["name"],
                            user_id=data["user_id"],
                            dataset_id=data["dataset_id"],
                            problem_type=data["problem_type"],
                            target_column=data["target_column"],
                            model_path=data["model_path"],
                            best_model_name=data.get("best_model_name", ""),
                            best_score=data.get("best_score", 0.0),
                            metric=data.get("metric", ""),
                            leaderboard=leaderboard,
                            feature_importance=data.get("feature_importance", {}),
                            algorithms_used=data.get("algorithms_used", []),
                            time_limit=data.get("time_limit", 300),
                            presets=data.get("presets", "medium_quality"),
                            session_id=data.get("session_id"),
                            created_at=datetime.fromisoformat(data["created_at"]),
                        )
                        self._models[str(model.id)] = model
                except Exception:
                    pass

    def _save_to_disk(self, model: MLModel):
        """Persist model metadata to disk"""
        meta_file = MODELS_META_DIR / f"{model.id}.json"
        data = {
            "id": str(model.id),
            "name": model.name,
            "user_id": model.user_id,
            "dataset_id": model.dataset_id,
            "problem_type": model.problem_type,
            "target_column": model.target_column,
            "model_path": model.model_path,
            "best_model_name": model.best_model_name,
            "best_score": model.best_score,
            "metric": model.metric,
            "leaderboard": [e.to_dict() for e in model.leaderboard],
            "feature_importance": model.feature_importance,
            "algorithms_used": model.algorithms_used,
            "time_limit": model.time_limit,
            "presets": model.presets,
            "session_id": model.session_id,
            "created_at": model.created_at.isoformat(),
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def save(self, model: MLModel) -> None:
        self._models[str(model.id)] = model
        self._save_to_disk(model)

    async def get_by_id(self, model_id: ModelId) -> Optional[MLModel]:
        return self._models.get(str(model_id))

    async def find_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[MLModel]:
        return [
            m for m in self._models.values()
            if m.belongs_to(user_id, session_id)
        ]

    async def delete(self, model_id: ModelId) -> bool:
        key = str(model_id)
        if key in self._models:
            model = self._models[key]
            # Delete model files
            model_path = Path(model.model_path)
            if model_path.exists():
                import shutil
                shutil.rmtree(model_path)

            del self._models[key]
            meta_file = MODELS_META_DIR / f"{key}.json"
            if meta_file.exists():
                meta_file.unlink()
            return True
        return False


class InMemoryJobRepository(JobRepository):
    """In-memory implementation of JobRepository"""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        """Load jobs from disk on startup"""
        if JOBS_META_DIR.exists():
            for job_file in JOBS_META_DIR.glob("*.json"):
                try:
                    with open(job_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        job = Job(
                            id=JobId.from_string(data["id"]),
                            job_type=JobType(data["job_type"]),
                            user_id=data["user_id"],
                            dataset_id=data["dataset_id"],
                            status=JobStatus(data["status"]),
                            progress=data.get("progress", 0.0),
                            status_message=data.get("status_message", ""),
                            config=data.get("config", {}),
                            model_id=data.get("model_id"),
                            result=data.get("result"),
                            error_message=data.get("error_message"),
                            session_id=data.get("session_id"),
                            created_at=datetime.fromisoformat(data["created_at"]),
                            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
                            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
                        )
                        self._jobs[str(job.id)] = job
                except Exception:
                    pass

    def _save_to_disk(self, job: Job):
        """Persist job to disk"""
        job_file = JOBS_META_DIR / f"{job.id}.json"
        data = {
            "id": str(job.id),
            "job_type": job.job_type.value,
            "user_id": job.user_id,
            "dataset_id": job.dataset_id,
            "status": job.status.value,
            "progress": job.progress,
            "status_message": job.status_message,
            "config": job.config,
            "model_id": job.model_id,
            "result": job.result,
            "error_message": job.error_message,
            "session_id": job.session_id,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def save(self, job: Job) -> None:
        self._jobs[str(job.id)] = job
        self._save_to_disk(job)

    async def get_by_id(self, job_id: JobId) -> Optional[Job]:
        return self._jobs.get(str(job_id))

    async def find_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[Job]:
        return [
            j for j in self._jobs.values()
            if j.belongs_to(user_id, session_id)
        ]

    async def find_pending(self) -> List[Job]:
        return [
            j for j in self._jobs.values()
            if j.status == JobStatus.PENDING
        ]

    async def update(self, job: Job) -> None:
        self._jobs[str(job.id)] = job
        self._save_to_disk(job)

    async def delete(self, job_id: JobId) -> bool:
        key = str(job_id)
        if key in self._jobs:
            del self._jobs[key]
            job_file = JOBS_META_DIR / f"{key}.json"
            if job_file.exists():
                job_file.unlink()
            return True
        return False
