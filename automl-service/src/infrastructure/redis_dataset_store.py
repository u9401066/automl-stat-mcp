"""
Redis Dataset Store

Shared dataset metadata storage in Redis.
Both automl-service and stats-service can access this.
Uses shared RedisManager for connection pooling.

Key format: datasets:{dataset_id}
Value: JSON with dataset metadata
"""

import json
import logging

# Import shared RedisManager
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from shared.infrastructure.redis_manager import get_sync_client

logger = logging.getLogger(__name__)

# Redis key prefix for datasets
DATASETS_KEY_PREFIX = "datasets:"
DATASETS_BY_USER_PREFIX = "datasets:user:"

# TTL for dataset metadata (30 days)
DATASET_TTL = 2592000


class RedisDatasetStore:
    """
    Redis-based dataset metadata storage using shared RedisManager.

    Provides shared access to dataset information across services.
    """

    def __init__(self):
        # Lazy initialization - get client from RedisManager on first use
        self._redis = None

    def _get_client(self) -> redis.Redis:
        """Get Redis client from shared connection pool."""
        if self._redis is None:
            self._redis = get_sync_client()
        return self._redis

    def save_dataset(self, dataset_info: Dict[str, Any]) -> None:
        """
        Save dataset metadata to Redis.

        Args:
            dataset_info: Dict with keys:
                - dataset_id: str
                - name: str
                - minio_path: str
                - user_id: str
                - columns: List[str]
                - row_count: int
                - file_size_bytes: int
                - created_at: str (ISO format)
                - description: Optional[str]
                - session_id: Optional[str]

        Raises:
            ConnectionError: If Redis connection fails
            RedisError: For other Redis errors
        """
        dataset_id = dataset_info["dataset_id"]
        user_id = dataset_info["user_id"]

        try:
            redis_client = self._get_client()

            # Store dataset metadata with TTL
            key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
            redis_client.set(key, json.dumps(dataset_info), ex=DATASET_TTL)

            # Add to user's dataset set for quick lookup
            user_key = f"{DATASETS_BY_USER_PREFIX}{user_id}"
            redis_client.sadd(user_key, dataset_id)
            # Set TTL on user set as well
            redis_client.expire(user_key, DATASET_TTL)

            logger.info(f"Saved dataset {dataset_id} to Redis with TTL {DATASET_TTL}s")

        except ConnectionError as e:
            logger.error(f"Redis connection failed while saving dataset {dataset_id}: {e}")
            raise
        except TimeoutError as e:
            logger.error(f"Redis timeout while saving dataset {dataset_id}: {e}")
            raise
        except RedisError as e:
            logger.error(f"Redis error while saving dataset {dataset_id}: {e}")
            raise

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get dataset metadata by ID.

        Returns:
            Dataset info dict or None if not found
        """
        redis_client = self._get_client()
        key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
        data = redis_client.get(key)

        if data:
            return json.loads(data)
        return None

    def get_datasets_by_user(self, user_id: str, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all datasets for a user.

        Args:
            user_id: User ID
            session_id: Optional session filter

        Returns:
            List of dataset info dicts
        """
        redis_client = self._get_client()
        user_key = f"{DATASETS_BY_USER_PREFIX}{user_id}"
        dataset_ids = redis_client.smembers(user_key)

        datasets = []
        for dataset_id in dataset_ids:
            dataset = self.get_dataset(dataset_id)
            if dataset:
                # Filter by session if specified
                if session_id is None or dataset.get("session_id") == session_id:
                    datasets.append(dataset)

        return datasets

    def delete_dataset(self, dataset_id: str, user_id: str) -> bool:
        """
        Delete dataset metadata.

        Returns:
            True if deleted, False if not found
        """
        redis_client = self._get_client()
        key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
        user_key = f"{DATASETS_BY_USER_PREFIX}{user_id}"

        # Remove from user's set
        redis_client.srem(user_key, dataset_id)

        # Delete metadata
        deleted = redis_client.delete(key)

        if deleted:
            logger.info(f"Deleted dataset {dataset_id} from Redis")

        return deleted > 0

    def dataset_exists(self, dataset_id: str) -> bool:
        """Check if dataset exists"""
        key = f"{DATASETS_KEY_PREFIX}{dataset_id}"
        return self._redis.exists(key) > 0


# Singleton instance
redis_dataset_store = RedisDatasetStore()
