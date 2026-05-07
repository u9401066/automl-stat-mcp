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
from typing import Any, BinaryIO, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


CSV_ENCODING_CANDIDATES = (
    "utf-8-sig",
    "utf-8",
    "utf-16",
    "utf-16le",
    "utf-16be",
    "cp950",
    "big5",
    "latin1",
)


def _raise_if_decoded_frame_is_suspicious(df: pd.DataFrame, encoding: str) -> None:
    """Reject decodes that technically succeed but leave UTF-16 NUL artifacts."""
    for column in df.columns:
        if "\x00" in str(column):
            raise UnicodeError(f"CSV decoded with {encoding!r} contains NUL column text")

    object_columns = df.select_dtypes(include=["object"]).columns[:10]
    for column in object_columns:
        sample = df[column].dropna().astype(str).head(20)
        if any("\x00" in value for value in sample):
            raise UnicodeError(f"CSV decoded with {encoding!r} contains NUL cell text")


def _read_csv_with_fallback(source, n_rows: Optional[int] = None) -> pd.DataFrame:
    """Read CSV with UTF-first fallback for Windows/Taiwan locale exports."""
    last_error: Exception | None = None
    for encoding in CSV_ENCODING_CANDIDATES:
        try:
            kwargs: dict[str, Any] = {"encoding": encoding}
            if n_rows is not None:
                kwargs["nrows"] = n_rows
            if isinstance(source, (bytes, bytearray)):
                df = pd.read_csv(io.BytesIO(source), **kwargs)
            else:
                df = pd.read_csv(source, **kwargs)
            _raise_if_decoded_frame_is_suspicious(df, encoding)
            return df
        except UnicodeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    if n_rows:
        return pd.read_csv(source, nrows=n_rows)
    return pd.read_csv(source)


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

    @abstractmethod
    async def get_file_info(self, path: str) -> dict[str, Any]:
        """Get file metadata such as size and modified time."""
        ...

    @abstractmethod
    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        """Validate CSV structure and return (is_valid, columns, row_count)."""
        ...

    @abstractmethod
    async def upload_content(
        self,
        path: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload raw content stream. Returns final path."""
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
            return _read_csv_with_fallback(file_path, n_rows=n_rows)
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
            with open(file_path, encoding="utf-8") as f:
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
        with open(file_path, "w", encoding="utf-8") as f:
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

    async def get_file_info(self, path: str) -> dict[str, Any]:
        """Get local file metadata."""
        file_path = self._resolve_path(path)
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        stat = file_path.stat()
        return {
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        """Validate local CSV readability and basic shape."""
        file_path = self._resolve_path(path)
        try:
            df = _read_csv_with_fallback(file_path)
        except Exception as exc:
            logger.error(f"Failed to validate CSV {file_path}: {exc}")
            return False, [], 0

        return True, df.columns.tolist(), len(df)

    async def upload_content(
        self,
        path: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Persist uploaded content into local storage root."""
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode("utf-8")
        file_path.write_bytes(data)
        return str(file_path)


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

            return _read_csv_with_fallback(data, n_rows=n_rows)
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

    async def get_file_info(self, path: str) -> dict[str, Any]:
        """Get MinIO object metadata."""
        bucket, object_name = self._parse_path(path)
        try:
            stat = self.client.stat_object(bucket, object_name)
        except Exception as exc:
            raise ValueError(f"Failed to stat object {bucket}/{object_name}: {exc}") from exc

        return {
            "size": stat.size,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
            "etag": stat.etag,
            "content_type": stat.content_type,
        }

    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        """Validate MinIO CSV readability and basic shape."""
        df = await self.read_csv(path)
        if df is None:
            return False, [], 0
        return True, df.columns.tolist(), len(df)

    async def upload_content(
        self,
        path: str,
        content: BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload content stream to MinIO."""
        bucket, object_name = self._parse_path(path)
        self._ensure_bucket(bucket)

        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode("utf-8")

        self.client.put_object(
            bucket,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )
        return f"{bucket}/{object_name}"


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
