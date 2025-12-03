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
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
    MINIO_SECURE, MINIO_DATASET_BUCKET, MINIO_REPORTS_BUCKET,
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


# Singleton instance
minio_client = MinioClient()
