"""
MinIO File Storage Service Implementation

All file storage is on MinIO - no local file storage.
"""
import io
from typing import Any, Dict, List, Tuple

import pandas as pd
from minio import Minio
from minio.error import S3Error

from ..config import MINIO_ACCESS_KEY, MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECRET_KEY, MINIO_SECURE
from ..domain.services import FileStorageService


class MinIOStorageService(FileStorageService):
    """MinIO implementation of FileStorageService"""

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        self.default_bucket = MINIO_BUCKET
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the default bucket exists"""
        try:
            if not self.client.bucket_exists(self.default_bucket):
                self.client.make_bucket(self.default_bucket)
        except S3Error:
            pass

    def _parse_path(self, path: str) -> Tuple[str, str]:
        """
        Parse path into bucket and object name.

        Supports formats:
        - "s3://bucket/path/to/file.csv"
        - "minio://bucket/path/to/file.csv"
        - "bucket/path/to/file.csv"
        - "path/to/file.csv" (uses default bucket)
        """
        # Remove s3:// or minio:// prefix
        if path.startswith("s3://"):
            path = path[5:]
        elif path.startswith("minio://"):
            path = path[8:]

        if "/" in path:
            parts = path.split("/", 1)
            # Check if first part is a valid bucket
            try:
                if self.client.bucket_exists(parts[0]):
                    return parts[0], parts[1]
            except S3Error:
                pass
            # Use default bucket
            return self.default_bucket, path

        return self.default_bucket, path

    async def file_exists(self, path: str) -> bool:
        """Check if file exists at the given path"""
        bucket, object_name = self._parse_path(path)
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download file from MinIO to local path"""
        bucket, object_name = self._parse_path(remote_path)
        self.client.fget_object(bucket, object_name, local_path)

    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file metadata"""
        bucket, object_name = self._parse_path(path)
        try:
            stat = self.client.stat_object(bucket, object_name)
            return {
                "size": stat.size,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                "etag": stat.etag,
                "content_type": stat.content_type,
            }
        except S3Error as e:
            raise ValueError(f"Failed to get file info: {e}") from e

    async def read_csv(self, path: str) -> pd.DataFrame:
        """Read CSV file from MinIO into DataFrame"""
        bucket, object_name = self._parse_path(path)
        try:
            response = self.client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            return pd.read_csv(io.BytesIO(data))
        except S3Error as e:
            raise ValueError(f"Failed to read CSV: {e}") from e

    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        """
        Validate CSV file format.

        Returns:
            Tuple of (is_valid, columns, row_count)
        """
        try:
            df = await self.read_csv(path)
            columns = df.columns.tolist()
            row_count = len(df)
            return True, columns, row_count
        except Exception:
            return False, [], 0

    async def upload_content(
        self,
        path: str,
        content: io.BytesIO,
        content_type: str = "application/octet-stream"
    ) -> None:
        """
        Upload content to MinIO.

        Args:
            path: Destination path (bucket/object_name)
            content: BytesIO content to upload
            content_type: MIME type of content
        """
        bucket, object_name = self._parse_path(path)

        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except S3Error:
            pass

        # Get content size
        content.seek(0, 2)  # Seek to end
        size = content.tell()
        content.seek(0)  # Seek back to start

        # Upload
        self.client.put_object(
            bucket,
            object_name,
            content,
            size,
            content_type=content_type,
        )


class LocalFileStorageService(FileStorageService):
    """
    Local file system implementation for testing without MinIO
    """

    async def file_exists(self, path: str) -> bool:
        from pathlib import Path
        return Path(path).exists()

    async def download_file(self, remote_path: str, local_path: str) -> None:
        import shutil
        shutil.copy(remote_path, local_path)

    async def get_file_info(self, path: str) -> Dict[str, Any]:
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            raise ValueError(f"File not found: {path}")
        stat = p.stat()
        return {
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
        }

    async def read_csv(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path)

    async def validate_csv(self, path: str) -> Tuple[bool, List[str], int]:
        try:
            df = pd.read_csv(path)
            return True, df.columns.tolist(), len(df)
        except Exception:
            return False, [], 0
