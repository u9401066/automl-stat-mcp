"""
Dependency Injection Container

Provides instances of repositories and services.
Uses Redis Queue for job management (not in-memory).
"""
import os
from functools import lru_cache

from ...infrastructure.repositories import (
    InMemoryDatasetRepository,
    InMemoryModelRepository,
)
from ...infrastructure.file_storage import MinIOStorageService
from ...infrastructure.queue.redis_queue import RedisJobQueue, get_job_queue
from ...config import MINIO_BUCKET


class Container:
    """Simple DI container for API service (no ML engine needed)"""
    
    _instance = None
    
    def __init__(self):
        # Repositories (in-memory for now, can move to Redis/DB later)
        self._dataset_repo = None
        self._model_repo = None
        
        # Services
        self._minio_client = None
        self._job_queue = None

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
    def file_storage(self) -> MinIOStorageService:
        """MinIO file storage service"""
        if self._minio_client is None:
            self._minio_client = MinIOStorageService()
        return self._minio_client

    @property
    def job_queue(self) -> RedisJobQueue:
        """Redis job queue"""
        if self._job_queue is None:
            self._job_queue = get_job_queue()
        return self._job_queue

    @property
    def dataset_bucket(self) -> str:
        """MinIO bucket for datasets"""
        return MINIO_BUCKET


def get_container() -> Container:
    return Container.get_instance()
