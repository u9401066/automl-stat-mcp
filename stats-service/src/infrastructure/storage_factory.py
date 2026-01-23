"""
Storage Factory - Unified storage abstraction for local and MinIO storage.

Usage:
    from .storage_factory import get_storage

    storage = get_storage()
    df = await storage.read_csv("/data/sample_data/iris.csv")

Environment Variables:
    STORAGE_MODE: "local" (default) or "minio"
    LOCAL_DATA_ROOT: Root path for local storage (default: /data)
"""
import io
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# Abstract Storage Interface
# =============================================================================


class StorageService(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def read_csv(
        self,
        path: str,
        n_rows: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """Read CSV file into DataFrame."""
        ...

    @abstractmethod
    async def write_csv(
        self,
        path: str,
        df: pd.DataFrame,
    ) -> str:
        """Write DataFrame to CSV file. Returns final path."""
        ...

    @abstractmethod
    async def read_json(self, path: str) -> Optional[dict]:
        """Read JSON file."""
        ...

    @abstractmethod
    async def write_json(
        self,
        path: str,
        data: dict,
    ) -> str:
        """Write dict to JSON file. Returns final path."""
        ...

    @abstractmethod
    async def read_bytes(self, path: str) -> Optional[bytes]:
        """Read raw bytes from file."""
        ...

    @abstractmethod
    async def write_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Write raw bytes to file. Returns final path."""
        ...

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        ...

    @abstractmethod
    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[dict]:
        """List files in directory/prefix."""
        ...

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file. Returns True if deleted."""
        ...

    @abstractmethod
    def get_public_url(self, path: str) -> Optional[str]:
        """Get public URL for a file (if applicable)."""
        ...


# =============================================================================
# Local Storage Implementation
# =============================================================================


class LocalStorageService(StorageService):
    """
    Local file system storage implementation.

    Path resolution:
    - Relative paths are resolved from LOCAL_DATA_ROOT
    - Absolute paths are used as-is
    - Container paths (/data/...) are used directly
    """

    def __init__(self, data_root: str = "/data"):
        self.data_root = Path(data_root)
        logger.info(f"LocalStorageService initialized with root: {self.data_root}")

    def _resolve_path(self, path: str) -> Path:
        """Resolve path to absolute local path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.data_root / path

    async def read_csv(
        self,
        path: str,
        n_rows: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """Read CSV file into DataFrame."""
        file_path = self._resolve_path(path)
        try:
            if n_rows:
                return pd.read_csv(file_path, nrows=n_rows)
            return pd.read_csv(file_path)
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to read CSV {file_path}: {e}")
            return None

    async def write_csv(
        self,
        path: str,
        df: pd.DataFrame,
    ) -> str:
        """Write DataFrame to CSV file."""
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(file_path, index=False)
        return str(file_path)

    async def read_json(self, path: str) -> Optional[dict]:
        """Read JSON file."""
        file_path = self._resolve_path(path)
        try:
            with open(file_path) as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to read JSON {file_path}: {e}")
            return None

    async def write_json(
        self,
        path: str,
        data: dict,
    ) -> str:
        """Write dict to JSON file."""
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return str(file_path)

    async def read_bytes(self, path: str) -> Optional[bytes]:
        """Read raw bytes from file."""
        file_path = self._resolve_path(path)
        try:
            return file_path.read_bytes()
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to read bytes {file_path}: {e}")
            return None

    async def write_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Write raw bytes to file."""
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return str(file_path)

    async def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        return self._resolve_path(path).exists()

    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[dict]:
        """List files in directory."""
        dir_path = self._resolve_path(path)
        if not dir_path.exists():
            return []

        files = []
        glob_fn = dir_path.rglob if recursive else dir_path.glob
        for p in glob_fn(pattern):
            if p.is_file():
                stat = p.stat()
                files.append({
                    "name": str(p.relative_to(dir_path)),
                    "path": str(p),
                    "size": stat.st_size,
                    "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        return files

    async def delete_file(self, path: str) -> bool:
        """Delete a file."""
        file_path = self._resolve_path(path)
        try:
            file_path.unlink()
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")
            return False

    def get_public_url(self, path: str) -> Optional[str]:
        """Local files don't have public URLs."""
        return None


# =============================================================================
# MinIO Storage Implementation
# =============================================================================


class MinIOStorageService(StorageService):
    """
    MinIO object storage implementation.

    Path format:
    - "bucket/path/to/file" - explicit bucket
    - "path/to/file" - uses default bucket
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
        default_bucket: str = "automl-datasets",
    ):
        from minio import Minio

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self.default_bucket = default_bucket
        self.endpoint = endpoint
        self.secure = secure
        logger.info(f"MinIOStorageService initialized: {endpoint}")

    def _parse_path(self, path: str) -> tuple[str, str]:
        """Parse path into (bucket, object_name)."""
        # Remove protocol prefix if present
        for prefix in ["s3://", "minio://", "http://", "https://"]:
            if path.startswith(prefix):
                path = path[len(prefix):]
                break

        if "/" in path:
            parts = path.split("/", 1)
            # Check if first part is a valid bucket
            try:
                if self.client.bucket_exists(parts[0]):
                    return parts[0], parts[1]
            except Exception:
                pass
        return self.default_bucket, path

    def _ensure_bucket(self, bucket: str) -> None:
        """Ensure bucket exists."""
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")
        except Exception as e:
            logger.warning(f"Failed to create bucket {bucket}: {e}")

    async def read_csv(
        self,
        path: str,
        n_rows: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """Read CSV file from MinIO."""
        bucket, object_name = self._parse_path(path)
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            if n_rows:
                return pd.read_csv(io.BytesIO(data), nrows=n_rows)
            return pd.read_csv(io.BytesIO(data))
        except Exception as e:
            logger.error(f"Failed to read CSV {bucket}/{object_name}: {e}")
            return None

    async def write_csv(
        self,
        path: str,
        df: pd.DataFrame,
    ) -> str:
        """Write DataFrame to MinIO."""
        bucket, object_name = self._parse_path(path)
        self._ensure_bucket(bucket)

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        self.client.put_object(
            bucket,
            object_name,
            io.BytesIO(csv_bytes),
            len(csv_bytes),
            content_type="text/csv",
        )
        return f"{bucket}/{object_name}"

    async def read_json(self, path: str) -> Optional[dict]:
        """Read JSON file from MinIO."""
        bucket, object_name = self._parse_path(path)
        try:
            response = self.client.get_object(bucket, object_name)
            data = json.loads(response.read().decode("utf-8"))
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"Failed to read JSON {bucket}/{object_name}: {e}")
            return None

    async def write_json(
        self,
        path: str,
        data: dict,
    ) -> str:
        """Write dict to MinIO as JSON."""
        bucket, object_name = self._parse_path(path)
        self._ensure_bucket(bucket)

        json_bytes = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        self.client.put_object(
            bucket,
            object_name,
            io.BytesIO(json_bytes),
            len(json_bytes),
            content_type="application/json",
        )
        return f"{bucket}/{object_name}"

    async def read_bytes(self, path: str) -> Optional[bytes]:
        """Read raw bytes from MinIO."""
        bucket, object_name = self._parse_path(path)
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except Exception as e:
            logger.error(f"Failed to read bytes {bucket}/{object_name}: {e}")
            return None

    async def write_bytes(
        self,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Write raw bytes to MinIO."""
        bucket, object_name = self._parse_path(path)
        self._ensure_bucket(bucket)

        self.client.put_object(
            bucket,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )
        return f"{bucket}/{object_name}"

    async def file_exists(self, path: str) -> bool:
        """Check if file exists in MinIO."""
        bucket, object_name = self._parse_path(path)
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False

    async def list_files(
        self,
        path: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> List[dict]:
        """List files in MinIO bucket/prefix."""
        bucket, prefix = self._parse_path(path)

        files = []
        try:
            for obj in self.client.list_objects(bucket, prefix=prefix, recursive=recursive):
                # Basic pattern matching
                if pattern != "*":
                    import fnmatch
                    if not fnmatch.fnmatch(obj.object_name, pattern):
                        continue
                files.append({
                    "name": obj.object_name,
                    "path": f"{bucket}/{obj.object_name}",
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                })
        except Exception as e:
            logger.error(f"Failed to list files {bucket}/{prefix}: {e}")

        return files

    async def delete_file(self, path: str) -> bool:
        """Delete file from MinIO."""
        bucket, object_name = self._parse_path(path)
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete {bucket}/{object_name}: {e}")
            return False

    def get_public_url(self, path: str) -> Optional[str]:
        """Get pre-signed URL for MinIO object."""
        bucket, object_name = self._parse_path(path)
        try:
            from datetime import timedelta
            url = self.client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(hours=1),
            )
            return url
        except Exception as e:
            logger.error(f"Failed to get URL for {bucket}/{object_name}: {e}")
            return None


# =============================================================================
# Factory Function
# =============================================================================

# Singleton storage instance
_storage_instance: Optional[StorageService] = None


def get_storage() -> StorageService:
    """
    Get the configured storage service.

    Environment Variables:
        STORAGE_MODE: "local" (default) or "minio"
        LOCAL_DATA_ROOT: Root path for local storage (default: /data)
        MINIO_ENDPOINT: MinIO endpoint
        MINIO_ACCESS_KEY: MinIO access key
        MINIO_SECRET_KEY: MinIO secret key
        MINIO_SECURE: Use HTTPS (default: false)
        MINIO_DATASET_BUCKET: Default bucket (default: automl-datasets)

    Returns:
        StorageService instance
    """
    global _storage_instance

    if _storage_instance is not None:
        return _storage_instance

    storage_mode = os.getenv("STORAGE_MODE", "local").lower()

    if storage_mode == "minio":
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        default_bucket = os.getenv("MINIO_DATASET_BUCKET", "automl-datasets")

        _storage_instance = MinIOStorageService(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            default_bucket=default_bucket,
        )
        logger.info(f"Using MinIO storage: {endpoint}")
    else:
        data_root = os.getenv("LOCAL_DATA_ROOT", "/data")
        _storage_instance = LocalStorageService(data_root=data_root)
        logger.info(f"Using local storage: {data_root}")

    return _storage_instance


def reset_storage() -> None:
    """Reset storage singleton (for testing)."""
    global _storage_instance
    _storage_instance = None
