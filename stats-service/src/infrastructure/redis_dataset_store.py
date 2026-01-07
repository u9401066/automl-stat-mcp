"""
Redis Dataset Store

Shared dataset metadata storage in Redis.
Both automl-service and stats-service can access this.

Key format: datasets:{dataset_id}
Value: JSON with dataset metadata
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)

# Redis key prefix for datasets
DATASETS_KEY_PREFIX = "datasets:"
DATASETS_BY_USER_PREFIX = "datasets:user:"


class RedisDatasetStore:
    """
    Redis-based dataset metadata storage.

    Provides shared access to dataset information across services.
    """

    def __init__(self):
        self._redis = redis.Redis(
            host=os.environ.get("REDIS_HOST", "localhost"),
            port=int(os.environ.get("REDIS_PORT", "6379")),
            db=int(os.environ.get("REDIS_DB", "0")),
            decode_responses=True,
        )

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset metadata by ID.

        Returns:
            Dataset info dict or None if not found
        """
        key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
        data = self._redis.get(key)

        if data:
            return json.loads(data)
        return None

    def get_datasets_by_user(
        self,
        user_id: str,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all datasets for a user.

        Args:
            user_id: User ID
            session_id: Optional session filter

        Returns:
            List of dataset info dicts
        """
        user_key = f"{DATASETS_BY_USER_PREFIX}{user_id}"
        dataset_ids = self._redis.smembers(user_key)

        datasets = []
        for dataset_id in dataset_ids:
            dataset = self.get_dataset(dataset_id)
            if dataset:
                # Filter by session if specified
                if session_id is None or dataset.get("session_id") == session_id:
                    datasets.append(dataset)

        return datasets

    def dataset_exists(self, dataset_id: str) -> bool:
        """Check if dataset exists"""
        key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
        return self._redis.exists(key) > 0


# Singleton instance
redis_dataset_store = RedisDatasetStore()
