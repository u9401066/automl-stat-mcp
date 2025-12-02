"""
Dependency Injection Container

Provides instances of repositories and services.
"""
from functools import lru_cache

from ...infrastructure.repositories import (
    InMemoryDatasetRepository,
    InMemoryModelRepository,
    InMemoryJobRepository,
)
from ...infrastructure.storage import MinIOStorageService, LocalFileStorageService
from ...infrastructure.ml_engine import AutoGluonEngine
from ...infrastructure.job_worker import JobWorker


class Container:
    """Simple DI container"""
    
    _instance = None
    
    def __init__(self):
        # Repositories
        self._dataset_repo = None
        self._model_repo = None
        self._job_repo = None
        
        # Services
        self._file_storage = None
        self._ml_engine = None
        self._job_worker = None

    @classmethod
    def get_instance(cls) -> "Container":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def dataset_repo(self):
        if self._dataset_repo is None:
            self._dataset_repo = InMemoryDatasetRepository()
        return self._dataset_repo

    @property
    def model_repo(self):
        if self._model_repo is None:
            self._model_repo = InMemoryModelRepository()
        return self._model_repo

    @property
    def job_repo(self):
        if self._job_repo is None:
            self._job_repo = InMemoryJobRepository()
        return self._job_repo

    @property
    def file_storage(self):
        if self._file_storage is None:
            try:
                self._file_storage = MinIOStorageService()
            except Exception:
                # Fallback to local storage for testing
                self._file_storage = LocalFileStorageService()
        return self._file_storage

    @property
    def ml_engine(self):
        if self._ml_engine is None:
            self._ml_engine = AutoGluonEngine()
        return self._ml_engine

    @property
    def job_worker(self):
        if self._job_worker is None:
            self._job_worker = JobWorker(
                job_repo=self.job_repo,
                dataset_repo=self.dataset_repo,
                model_repo=self.model_repo,
                ml_engine=self.ml_engine,
                file_storage=self.file_storage,
            )
        return self._job_worker


def get_container() -> Container:
    return Container.get_instance()
