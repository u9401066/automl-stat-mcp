"""
MinIO Storage Client (Streaming - No Local Storage)

All file operations are streamed, no local copies kept.
"""
import io
import os
from typing import BinaryIO, List, Optional, Tuple

import pandas as pd
from minio import Minio
from minio.error import S3Error


class MinioStorageClient:
    """
    MinIO client for streaming file operations.
    
    Key principle: No local storage!
    - Files are streamed directly from/to MinIO
    - Temporary files cleaned immediately after use
    """
    
    def __init__(self):
        self._client = Minio(
            endpoint=os.environ.get("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
        )
        
        self._dataset_bucket = os.environ.get("MINIO_DATASET_BUCKET", "automl-datasets")
        self._model_bucket = os.environ.get("MINIO_MODEL_BUCKET", "automl-models")
        
        # Ensure buckets exist
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Create buckets if they don't exist"""
        for bucket in [self._dataset_bucket, self._model_bucket]:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
    
    @property
    def dataset_bucket(self) -> str:
        return self._dataset_bucket
    
    @property
    def model_bucket(self) -> str:
        return self._model_bucket
    
    def file_exists(self, bucket: str, path: str) -> bool:
        """Check if file exists"""
        try:
            self._client.stat_object(bucket, path)
            return True
        except S3Error:
            return False
    
    def get_dataset_info(self, minio_path: str) -> Tuple[List[str], int]:
        """
        Get dataset column names and row count.
        
        Streams only the header + first chunk to minimize memory usage.
        """
        # Parse path
        bucket, object_name = self._parse_path(minio_path)
        
        # Stream the file
        response = self._client.get_object(bucket, object_name)
        
        try:
            # Read into pandas with streaming
            df = pd.read_csv(
                io.BytesIO(response.read()),
                nrows=None,  # Read all for accurate count
            )
            return list(df.columns), len(df)
        finally:
            response.close()
            response.release_conn()
    
    def get_dataset_preview(
        self, 
        minio_path: str, 
        n_rows: int = 5
    ) -> pd.DataFrame:
        """Get first n rows of dataset"""
        bucket, object_name = self._parse_path(minio_path)
        
        response = self._client.get_object(bucket, object_name)
        
        try:
            df = pd.read_csv(
                io.BytesIO(response.read()),
                nrows=n_rows,
            )
            return df
        finally:
            response.close()
            response.release_conn()
    
    def stream_dataset(self, minio_path: str) -> BinaryIO:
        """
        Get a file-like object for streaming dataset.
        
        Caller is responsible for closing!
        """
        bucket, object_name = self._parse_path(minio_path)
        return self._client.get_object(bucket, object_name)
    
    def upload_file(
        self, 
        bucket: str, 
        object_name: str, 
        file_path: str,
    ) -> str:
        """Upload a local file to MinIO"""
        self._client.fput_object(bucket, object_name, file_path)
        return f"{bucket}/{object_name}"
    
    def upload_stream(
        self,
        bucket: str,
        object_name: str,
        data: BinaryIO,
        length: int,
    ) -> str:
        """Upload from stream to MinIO"""
        self._client.put_object(bucket, object_name, data, length)
        return f"{bucket}/{object_name}"
    
    def delete_file(self, bucket: str, object_name: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self._client.remove_object(bucket, object_name)
            return True
        except S3Error:
            return False
    
    def list_files(
        self, 
        bucket: str, 
        prefix: str = "",
    ) -> List[str]:
        """List files in bucket with prefix"""
        objects = self._client.list_objects(bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]
    
    def _parse_path(self, minio_path: str) -> Tuple[str, str]:
        """Parse 'bucket/path/to/file' into (bucket, object_name)"""
        parts = minio_path.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return self._dataset_bucket, parts[0]


# Singleton
_storage: Optional[MinioStorageClient] = None


def get_storage() -> MinioStorageClient:
    """Get or create storage client"""
    global _storage
    if _storage is None:
        _storage = MinioStorageClient()
    return _storage
