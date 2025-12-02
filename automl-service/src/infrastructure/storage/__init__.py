"""
Storage Infrastructure

MinIO client for streaming file operations.
"""
from .minio_client import MinioStorageClient, get_storage

__all__ = ["MinioStorageClient", "get_storage"]
