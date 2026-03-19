"""
Result Storage Service for MCP Statistics Tools

Provides persistent storage for analysis results:
- Redis: Quick access with TTL (7 days default)
- MinIO: Permanent storage with organized file structure

This module enables all statistics tools to automatically save results
for reproducibility, tracking, and report generation.
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types and other special types."""

    def default(self, obj):
        # Handle numpy types
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        # Handle pandas types if present
        elif hasattr(obj, "item"):  # pandas scalars
            return obj.item()
        # Handle datetime
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # Handle boolean (should be handled by default, but just in case)
        elif isinstance(obj, bool):
            return obj
        # Handle bytes
        elif isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        # Handle sets
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize data to JSON string, handling numpy and other special types."""
    return json.dumps(data, cls=NumpyJSONEncoder, ensure_ascii=False, **kwargs)


# Configuration from environment
STATS_SERVICE_URL = os.getenv("STATS_SERVICE_URL", "http://localhost:8003")
AUTOML_SERVICE_URL = os.getenv("AUTOML_SERVICE_URL", "http://localhost:8001")
MINIO_BUCKET = os.getenv("MINIO_RESULTS_BUCKET", "automl-results")

# Default TTL for Redis (7 days)
DEFAULT_REDIS_TTL = 7 * 24 * 60 * 60


@dataclass
class ResultMetadata:
    """Metadata for a stored analysis result"""

    result_id: str
    analysis_type: str
    user_id: str
    created_at: str
    redis_key: str
    minio_path: Optional[str] = None
    expires_at: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


class ResultStorage:
    """
    Service for storing and retrieving analysis results.

    Storage hierarchy:
    1. Redis (fast, temporary): TTL 7 days
       - Key: stats:result:{result_id}
       - Full result JSON

    2. MinIO (persistent):
       - Path: {bucket}/{user_id}/{analysis_type}/{timestamp}_{result_id}.json
       - Full result JSON + metadata

    Usage:
        storage = ResultStorage()

        # Save a result
        metadata = await storage.save_result(
            result={"status": "success", "data": {...}},
            user_id="eric",
            analysis_type="tableone",
        )

        # Get result back
        result = await storage.get_result(metadata.result_id)
    """

    def __init__(
        self,
        stats_service_url: str = STATS_SERVICE_URL,
        automl_service_url: str = AUTOML_SERVICE_URL,
        minio_bucket: str = MINIO_BUCKET,
    ):
        self.stats_service_url = stats_service_url
        self.automl_service_url = automl_service_url
        self.minio_bucket = minio_bucket
        self.timeout = 30

    def _generate_result_id(self, analysis_type: str) -> str:
        """Generate a unique result ID"""
        short_uuid = uuid.uuid4().hex[:8]
        return f"stat_{analysis_type}_{short_uuid}"

    def _get_minio_path(
        self,
        user_id: str,
        analysis_type: str,
        result_id: str,
        file_format: str = "json",
    ) -> str:
        """Generate MinIO path for result storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{user_id}/{analysis_type}/{timestamp}_{result_id}.{file_format}"

    async def save_result(
        self,
        result: Dict[str, Any],
        user_id: str,
        analysis_type: str,
        summary: Optional[Dict[str, Any]] = None,
        save_to_minio: bool = True,
        redis_ttl: int = DEFAULT_REDIS_TTL,
        file_format: str = "json",
    ) -> ResultMetadata:
        """
        Save analysis result to Redis and optionally MinIO.

        Args:
            result: The analysis result dictionary
            user_id: User identifier
            analysis_type: Type of analysis (tableone, correlation, roc, etc.)
            summary: Optional summary for quick reference
            save_to_minio: Whether to persist to MinIO (default True)
            redis_ttl: Redis TTL in seconds (default 7 days)
            file_format: Output format (json, csv, markdown)

        Returns:
            ResultMetadata with storage locations
        """
        result_id = self._generate_result_id(analysis_type)
        redis_key = f"stats:result:{result_id}"
        created_at = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(seconds=redis_ttl)).isoformat()

        # Prepare metadata
        metadata = ResultMetadata(
            result_id=result_id,
            analysis_type=analysis_type,
            user_id=user_id,
            created_at=created_at,
            redis_key=redis_key,
            expires_at=expires_at,
            summary=summary or self._extract_summary(result, analysis_type),
        )

        # Prepare full result with metadata
        full_result = {
            "metadata": {
                "result_id": result_id,
                "analysis_type": analysis_type,
                "user_id": user_id,
                "created_at": created_at,
            },
            "result": result,
        }

        # 1. Save to Redis via Stats Service
        try:
            await self._save_to_redis(redis_key, full_result, redis_ttl)
            logger.info(f"Saved result to Redis: {redis_key}")
        except Exception as e:
            logger.error(f"Failed to save to Redis: {e}")
            # Continue anyway - MinIO might work

        # 2. Save to MinIO if requested
        if save_to_minio:
            try:
                minio_path = self._get_minio_path(user_id, analysis_type, result_id, file_format)
                await self._save_to_minio(minio_path, full_result, file_format)
                metadata.minio_path = f"{self.minio_bucket}/{minio_path}"
                logger.info(f"Saved result to MinIO: {metadata.minio_path}")
            except Exception as e:
                logger.error(f"Failed to save to MinIO: {e}")

        return metadata

    async def get_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a result by ID.

        First tries Redis, then falls back to MinIO.
        """
        redis_key = f"stats:result:{result_id}"

        # Try Redis first
        try:
            result = await self._get_from_redis(redis_key)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Redis lookup failed: {e}")

        # TODO: Fall back to MinIO lookup
        # Would need to query by result_id pattern

        return None

    async def list_results(
        self,
        user_id: str,
        analysis_type: Optional[str] = None,
        limit: int = 20,
    ) -> list:
        """List recent results for a user"""
        # This would query Redis or MinIO for user's results
        # For now, return empty - need to implement index
        return []

    def _extract_summary(self, result: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Extract a summary from the result for quick reference"""
        summary = {}

        if analysis_type == "tableone":
            summary["n_total"] = result.get("n_total")
            summary["n_variables"] = len(result.get("variables_analyzed", []))

        elif analysis_type == "correlation":
            summary["n_variables"] = len(result.get("columns", []))
            summary["n_significant_pairs"] = len(result.get("significant_pairs", []))

        elif analysis_type == "compare_groups":
            summary["n_groups"] = result.get("n_groups")
            summary["test_used"] = result.get("main_test", {}).get("test")
            summary["p_value"] = result.get("main_test", {}).get("p_value")

        elif analysis_type == "roc":
            summary["auc"] = result.get("auc")
            summary["optimal_threshold"] = result.get("optimal_threshold")

        return summary

    async def _save_to_redis(
        self,
        key: str,
        data: Dict[str, Any],
        ttl: int,
    ) -> None:
        """Save data to Redis via Stats Service API"""
        # Use safe_json_dumps to handle numpy types, then parse back for httpx
        json_str = safe_json_dumps(data)
        data_safe = json.loads(json_str)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.stats_service_url}/storage/redis/set",
                json={
                    "key": key,
                    "value": data_safe,
                    "ttl": ttl,
                },
            )
            response.raise_for_status()

    async def _get_from_redis(self, key: str) -> Optional[Dict[str, Any]]:
        """Get data from Redis via Stats Service API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.stats_service_url}/storage/redis/get",
                params={"key": key},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def _save_to_minio(
        self,
        path: str,
        data: Dict[str, Any],
        file_format: str,
    ) -> None:
        """Save data to MinIO via Stats Service API"""
        # Convert data based on format using safe encoder
        if file_format == "json":
            content = safe_json_dumps(data, indent=2)
            content_type = "application/json"
        elif file_format == "markdown":
            content = self._result_to_markdown(data)
            content_type = "text/markdown"
        else:
            content = safe_json_dumps(data)
            content_type = "application/json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.stats_service_url}/storage/minio/upload",
                json={
                    "bucket": self.minio_bucket,
                    "path": path,
                    "content": content,
                    "content_type": content_type,
                },
            )
            response.raise_for_status()

    def _result_to_markdown(self, data: Dict[str, Any]) -> str:
        """Convert result to Markdown format"""
        metadata = data.get("metadata", {})
        result = data.get("result", {})

        md_lines = [
            f"# Analysis Result: {metadata.get('analysis_type', 'Unknown')}",
            "",
            f"**Result ID**: {metadata.get('result_id')}",
            f"**User**: {metadata.get('user_id')}",
            f"**Created**: {metadata.get('created_at')}",
            "",
            "---",
            "",
            "## Result",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2),
            "```",
        ]

        return "\n".join(md_lines)


# Singleton instance
_result_storage: Optional[ResultStorage] = None


def get_result_storage() -> ResultStorage:
    """Get or create the ResultStorage singleton"""
    global _result_storage
    if _result_storage is None:
        _result_storage = ResultStorage()
    return _result_storage
