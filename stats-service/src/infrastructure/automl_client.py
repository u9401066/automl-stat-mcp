"""
Stats Service - AutoML Client

Handles communication with AutoML Service to get dataset information.
"""
import logging
from typing import Any, Dict, Optional

import httpx

from ..config import AUTOML_SERVICE_URL

logger = logging.getLogger(__name__)


class AutoMLClient:
    """Client for querying AutoML Service"""

    def __init__(self):
        self.base_url = AUTOML_SERVICE_URL
        self.timeout = 30

    async def get_dataset_info(self, dataset_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset information from AutoML Service.

        Returns:
            Dataset info including minio_path, or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Query automl-service for dataset
                response = await client.get(
                    f"{self.base_url}/datasets",
                    params={"user_id": user_id},
                    headers={"x-user-id": user_id}
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get datasets: {response.status_code}")
                    return None

                data = response.json()
                # API returns array directly, not {"datasets": [...]}
                datasets = data if isinstance(data, list) else data.get("datasets", [])

                # Find matching dataset
                for ds in datasets:
                    if ds.get("dataset_id") == dataset_id:
                        return {
                            "dataset_id": ds.get("dataset_id"),
                            "name": ds.get("name"),
                            "minio_path": ds.get("minio_path"),
                            "columns": ds.get("columns", []),
                            "row_count": ds.get("row_count"),
                        }

                logger.warning(f"Dataset {dataset_id} not found for user {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error querying AutoML service: {e}")
            return None


# Singleton instance
automl_client = AutoMLClient()
