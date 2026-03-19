"""
HTTP Client for AutoML Service

Handles communication with the AutoML REST API.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from .config import default_config


@dataclass
class AutoMLClient:
    """Client for AutoML Service REST API"""

    base_url: str = default_config.automl_service_url
    timeout: int = default_config.http_timeout

    async def _request(
        self,
        method: str,
        path: str,
        user_id: str,
        session_id: Optional[str] = None,
        json: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to AutoML Service"""
        headers = {"X-User-Id": user_id}
        if session_id:
            headers["X-Session-Id"] = session_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                json=json,
            )
            response.raise_for_status()
            return response.json()

    # ============== Dataset Operations ==============

    async def register_dataset(
        self,
        name: str,
        minio_path: str,
        user_id: str,
        session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a dataset from MinIO"""
        return await self._request(
            "POST",
            "/datasets/register",
            user_id=user_id,
            session_id=session_id,
            json={
                "name": name,
                "minio_path": minio_path,
                "description": description,
            },
        )

    async def list_datasets(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List user's datasets"""
        return await self._request(
            "GET",
            "/datasets",
            user_id=user_id,
            session_id=session_id,
        )

    async def delete_dataset(
        self,
        dataset_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Delete a dataset"""
        return await self._request(
            "DELETE",
            f"/datasets/{dataset_id}",
            user_id=user_id,
        )

    async def upload_csv_content(
        self,
        name: str,
        csv_content: str,
        user_id: str,
        session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload CSV content directly.

        MCP Server reads the file and passes content to AutoML service.
        This avoids Copilot handling file content (saves tokens).
        """
        return await self._request(
            "POST",
            "/datasets/upload",
            user_id=user_id,
            session_id=session_id,
            json={
                "name": name,
                "csv_content": csv_content,
                "description": description,
            },
        )

    # ============== Training Operations ==============

    async def submit_automl_job(
        self,
        dataset_id: str,
        target_column: str,
        problem_type: str,
        user_id: str,
        session_id: Optional[str] = None,
        time_limit: int = 300,
        presets: str = "medium_quality",
        metric: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit AutoML training job"""
        return await self._request(
            "POST",
            "/train/automl",
            user_id=user_id,
            session_id=session_id,
            json={
                "dataset_id": dataset_id,
                "target_column": target_column,
                "problem_type": problem_type,
                "time_limit": time_limit,
                "presets": presets,
                "metric": metric,
            },
        )

    async def submit_specific_job(
        self,
        dataset_id: str,
        target_column: str,
        problem_type: str,
        algorithms: List[str],
        user_id: str,
        session_id: Optional[str] = None,
        time_limit: int = 300,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Submit training job with specific algorithms"""
        return await self._request(
            "POST",
            "/train/specific",
            user_id=user_id,
            session_id=session_id,
            json={
                "dataset_id": dataset_id,
                "target_column": target_column,
                "problem_type": problem_type,
                "algorithms": algorithms,
                "time_limit": time_limit,
                "hyperparameters": hyperparameters,
            },
        )

    async def submit_compare_job(
        self,
        dataset_id: str,
        target_column: str,
        problem_type: str,
        algorithms: List[str],
        user_id: str,
        session_id: Optional[str] = None,
        time_limit: int = 300,
    ) -> Dict[str, Any]:
        """Submit job to compare algorithms"""
        return await self._request(
            "POST",
            "/train/compare",
            user_id=user_id,
            session_id=session_id,
            json={
                "dataset_id": dataset_id,
                "target_column": target_column,
                "problem_type": problem_type,
                "algorithms": algorithms,
                "time_limit": time_limit,
            },
        )

    # ============== Job Operations ==============

    async def get_job_status(
        self,
        job_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get job status"""
        return await self._request(
            "GET",
            f"/jobs/{job_id}",
            user_id=user_id,
        )

    async def list_jobs(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List user's jobs"""
        return await self._request(
            "GET",
            "/jobs",
            user_id=user_id,
            session_id=session_id,
        )

    async def cancel_job(
        self,
        job_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Cancel a job"""
        return await self._request(
            "POST",
            f"/jobs/{job_id}/cancel",
            user_id=user_id,
        )

    # ============== Model Operations ==============

    async def list_models(
        self,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List user's models"""
        return await self._request(
            "GET",
            "/models",
            user_id=user_id,
            session_id=session_id,
        )

    async def get_model_leaderboard(
        self,
        model_id: str,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Get model leaderboard"""
        return await self._request(
            "GET",
            f"/models/{model_id}/leaderboard",
            user_id=user_id,
        )

    async def predict(
        self,
        model_id: str,
        dataset_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Make predictions"""
        return await self._request(
            "POST",
            "/models/predict",
            user_id=user_id,
            json={
                "model_id": model_id,
                "dataset_id": dataset_id,
            },
        )

    async def delete_model(
        self,
        model_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Delete a model"""
        return await self._request(
            "DELETE",
            f"/models/{model_id}",
            user_id=user_id,
        )

    # ============== Info Operations ==============

    async def list_algorithms(self) -> Dict[str, Any]:
        """List available algorithms"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/algorithms")
            response.raise_for_status()
            return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """Health check"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/")
            response.raise_for_status()
            return response.json()

    # ============== Direct Analysis Operations ==============

    async def direct_analyze(
        self,
        csv_content: str,
        user_id: str,
        is_base64: bool = False,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze CSV data directly for ML preparation"""
        return await self._request(
            "POST",
            "/direct/analyze",
            user_id=user_id,
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
                "target_column": target_column,
            },
        )

    async def direct_quick_stats(
        self,
        csv_content: str,
        user_id: str,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        """Get quick statistics for CSV data"""
        return await self._request(
            "POST",
            "/direct/quick-stats",
            user_id=user_id,
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
            },
        )

    async def direct_preview(
        self,
        csv_content: str,
        user_id: str,
        is_base64: bool = False,
        n_rows: int = 10,
    ) -> Dict[str, Any]:
        """Preview CSV data before registration"""
        return await self._request(
            "POST",
            "/direct/preview",
            user_id=user_id,
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
                "n_rows": n_rows,
            },
        )


# Singleton client instance
_client: Optional[AutoMLClient] = None


def get_client() -> AutoMLClient:
    """Get or create the client instance"""
    global _client
    if _client is None:
        _client = AutoMLClient()
    return _client
