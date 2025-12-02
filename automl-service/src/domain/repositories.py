"""
Repository Interfaces - Domain Layer

These are abstract interfaces that define how domain objects are persisted.
Actual implementations are in the Infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from .models import Dataset, DatasetId, MLModel, ModelId, Job, JobId


class DatasetRepository(ABC):
    """Repository interface for Dataset aggregate"""

    @abstractmethod
    async def save(self, dataset: Dataset) -> None:
        """Save a dataset"""
        pass

    @abstractmethod
    async def get_by_id(self, dataset_id: DatasetId) -> Optional[Dataset]:
        """Get dataset by ID"""
        pass

    @abstractmethod
    async def find_by_user(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> List[Dataset]:
        """Find all datasets for a user/session"""
        pass

    @abstractmethod
    async def delete(self, dataset_id: DatasetId) -> bool:
        """Delete a dataset"""
        pass

    @abstractmethod
    async def exists(self, dataset_id: DatasetId) -> bool:
        """Check if dataset exists"""
        pass


class ModelRepository(ABC):
    """Repository interface for MLModel aggregate"""

    @abstractmethod
    async def save(self, model: MLModel) -> None:
        """Save a model"""
        pass

    @abstractmethod
    async def get_by_id(self, model_id: ModelId) -> Optional[MLModel]:
        """Get model by ID"""
        pass

    @abstractmethod
    async def find_by_user(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> List[MLModel]:
        """Find all models for a user/session"""
        pass

    @abstractmethod
    async def delete(self, model_id: ModelId) -> bool:
        """Delete a model"""
        pass


class JobRepository(ABC):
    """Repository interface for Job aggregate"""

    @abstractmethod
    async def save(self, job: Job) -> None:
        """Save a job"""
        pass

    @abstractmethod
    async def get_by_id(self, job_id: JobId) -> Optional[Job]:
        """Get job by ID"""
        pass

    @abstractmethod
    async def find_by_user(
        self, 
        user_id: str, 
        session_id: Optional[str] = None
    ) -> List[Job]:
        """Find all jobs for a user/session"""
        pass

    @abstractmethod
    async def find_pending(self) -> List[Job]:
        """Find all pending jobs"""
        pass

    @abstractmethod
    async def update(self, job: Job) -> None:
        """Update a job"""
        pass

    @abstractmethod
    async def delete(self, job_id: JobId) -> bool:
        """Delete a job"""
        pass
