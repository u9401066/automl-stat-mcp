"""
Stats Service - MinIO Client

Handles object storage operations for datasets and reports.
"""
import io
import logging
from typing import Optional

import pandas as pd
from minio import Minio
from minio.error import S3Error

from ..config import (
    MINIO_ACCESS_KEY,
    MINIO_DATASET_BUCKET,
    MINIO_ENDPOINT,
    MINIO_REPORTS_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)

logger = logging.getLogger(__name__)


class MinioClient:
    """MinIO client for object storage operations"""

    def __init__(self):
        self._client = None

    def _get_client(self) -> Minio:
        """Get or create MinIO client"""
        if self._client is None:
            self._client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
        return self._client

    def ensure_buckets(self):
        """Ensure required buckets exist"""
        client = self._get_client()

        for bucket in [MINIO_DATASET_BUCKET, MINIO_REPORTS_BUCKET]:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"Created bucket: {bucket}")

    def get_dataset_info(self, dataset_id: str) -> Optional[dict]:
        """Get dataset information without loading full data"""
        client = self._get_client()

        try:
            # Try direct path first
            stat = client.stat_object(MINIO_DATASET_BUCKET, f"{dataset_id}.csv")
            return {
                "object_name": f"{dataset_id}.csv",
                "size": stat.size,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
            }
        except S3Error:
            # Try finding by prefix
            objects = list(client.list_objects(
                MINIO_DATASET_BUCKET,
                prefix=dataset_id,
                recursive=True
            ))

            for obj in objects:
                if obj.object_name.endswith('.csv'):
                    return {
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                    }

        return None

    def load_dataset_by_path(
        self,
        minio_path: str,
        n_rows: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Load dataset from MinIO by path.

        Args:
            minio_path: Path in format 'bucket/path/to/file.csv' or 'path/to/file.csv'
            n_rows: Number of rows to load (None for all)
        """
        client = self._get_client()

        try:
            # Parse path: could be 'bucket/path' or just 'path' (use default bucket)
            if '/' in minio_path:
                parts = minio_path.split('/', 1)
                # Check if first part is a bucket name
                if client.bucket_exists(parts[0]):
                    bucket = parts[0]
                    object_name = parts[1]
                else:
                    bucket = MINIO_DATASET_BUCKET
                    object_name = minio_path
            else:
                bucket = MINIO_DATASET_BUCKET
                object_name = minio_path

            logger.info(f"Loading dataset from {bucket}/{object_name}")

            response = client.get_object(bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            if n_rows:
                df = pd.read_csv(io.BytesIO(data), nrows=n_rows)
            else:
                df = pd.read_csv(io.BytesIO(data))

            return df

        except Exception as e:
            logger.error(f"Failed to load dataset from {minio_path}: {e}")
            return None

    def load_dataset_preview(
        self,
        dataset_id: str,
        n_rows: int = 100
    ) -> Optional[pd.DataFrame]:
        """Load a preview of the dataset"""
        client = self._get_client()

        try:
            # Find the object
            info = self.get_dataset_info(dataset_id)
            if not info:
                return None

            response = client.get_object(
                MINIO_DATASET_BUCKET,
                info["object_name"]
            )

            data = response.read()
            response.close()
            response.release_conn()

            df = pd.read_csv(io.BytesIO(data), nrows=n_rows)
            return df

        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_id}: {e}")
            return None

    def get_report(self, job_id: str) -> Optional[dict]:
        """Get report from storage"""
        client = self._get_client()

        try:
            response = client.get_object(
                MINIO_REPORTS_BUCKET,
                f"{job_id}.json"
            )

            import json
            data = json.loads(response.read().decode('utf-8'))
            response.close()
            response.release_conn()

            return data

        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise

    def get_html_report(self, job_id: str) -> Optional[str]:
        """Get HTML report from storage"""
        client = self._get_client()

        try:
            response = client.get_object(
                MINIO_REPORTS_BUCKET,
                f"{job_id}.html"
            )

            html = response.read().decode('utf-8')
            response.close()
            response.release_conn()

            return html

        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise

    def list_datasets(self, prefix: str = "") -> list:
        """List available datasets"""
        client = self._get_client()

        datasets = []
        objects = client.list_objects(
            MINIO_DATASET_BUCKET,
            prefix=prefix,
            recursive=True
        )

        for obj in objects:
            if obj.object_name.endswith('.csv'):
                datasets.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                })

        return datasets

    # =========================================================================
    # Generic Storage Methods (for result persistence)
    # =========================================================================

    def ensure_bucket(self, bucket: str) -> None:
        """Ensure a specific bucket exists"""
        client = self._get_client()
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"Created bucket: {bucket}")

    def put_object(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        """Upload data to MinIO"""
        client = self._get_client()

        client.put_object(
            bucket,
            path,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"Uploaded to MinIO: {bucket}/{path}")

    def get_object(self, bucket: str, path: str) -> bytes:
        """Download data from MinIO"""
        client = self._get_client()

        response = client.get_object(bucket, path)
        data = response.read()
        response.close()
        response.release_conn()

        return data

    def list_objects(
        self,
        bucket: str,
        prefix: str = "",
        limit: int = 100,
    ) -> list:
        """List objects in a bucket"""
        client = self._get_client()

        objects = []
        for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
            objects.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
            })
            if len(objects) >= limit:
                break

        return objects


# Singleton instance
minio_client = MinioClient()
