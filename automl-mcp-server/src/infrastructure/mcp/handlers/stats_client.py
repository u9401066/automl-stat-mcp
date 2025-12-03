"""
HTTP Client for Stats Service

Handles communication with the Stats Service REST API.
"""
import os
import httpx
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# Stats service URL from environment
STATS_SERVICE_URL = os.getenv("STATS_SERVICE_URL", "http://localhost:8003")


@dataclass
class StatsClient:
    """Client for Stats Service REST API"""
    
    base_url: str = STATS_SERVICE_URL
    timeout: int = 30

    async def _request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Stats Service"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                params=params,
                json=json,
            )
            response.raise_for_status()
            return response.json()

    # ============== EDA Operations ==============
    
    async def submit_eda_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        title: Optional[str] = "EDA Report",
        minimal: bool = True,
    ) -> Dict[str, Any]:
        """Submit an EDA job"""
        return await self._request(
            "POST",
            "/eda/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "title": title,
                "minimal": minimal,
            },
        )
    
    async def preview_dataset(
        self,
        dataset_id: str,
        n_rows: int = 10,
    ) -> Dict[str, Any]:
        """Preview dataset"""
        return await self._request(
            "POST",
            "/eda/preview",
            params={"dataset_id": dataset_id, "n_rows": n_rows},
        )

    # ============== TableOne Operations ==============
    
    async def submit_tableone_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        columns: Optional[List[str]] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        groupby: Optional[str] = None,
        nonnormal: Optional[List[str]] = None,
        pval: bool = False,
    ) -> Dict[str, Any]:
        """Submit a TableOne job"""
        return await self._request(
            "POST",
            "/tableone/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "columns": columns,
                "categorical": categorical,
                "continuous": continuous,
                "groupby": groupby,
                "nonnormal": nonnormal,
                "pval": pval,
            },
        )
    
    async def get_column_suggestions(
        self,
        dataset_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get column type suggestions for TableOne"""
        return await self._request(
            "POST",
            "/tableone/columns",
            params={"dataset_id": dataset_id, "user_id": user_id},
        )

    # ============== Auto-Analyze Operations ==============
    
    async def submit_auto_analyze_job(
        self,
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an auto-analyze job"""
        return await self._request(
            "POST",
            "/auto-analyze/submit",
            json={
                "dataset_id": dataset_id,
                "user_id": user_id,
                "session_id": session_id,
                "target_column": target_column,
            },
        )
    
    async def get_auto_analyze_capabilities(self) -> Dict[str, Any]:
        """Get auto-analyze capabilities"""
        return await self._request(
            "GET",
            "/auto-analyze/capabilities",
        )

    # ============== Job Operations ==============
    
    async def get_job_status(
        self,
        job_id: str,
    ) -> Dict[str, Any]:
        """Get job status"""
        return await self._request(
            "GET",
            f"/jobs/{job_id}",
        )
    
    async def get_job_result(
        self,
        job_id: str,
    ) -> Dict[str, Any]:
        """Get job result"""
        return await self._request(
            "GET",
            f"/jobs/{job_id}/result",
        )
    
    async def list_jobs(
        self,
        user_id: str,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List jobs for a user"""
        params = {"user_id": user_id, "limit": limit}
        if job_type:
            params["job_type"] = job_type
        
        return await self._request(
            "GET",
            "/jobs/",
            params=params,
        )
    
    async def delete_job(
        self,
        job_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Delete a job"""
        return await self._request(
            "DELETE",
            f"/jobs/{job_id}",
            params={"user_id": user_id},
        )
    
    # ============== Direct Analysis ==============
    
    async def direct_analyze(
        self,
        csv_content: str,
        user_id: str,
        target_column: Optional[str] = None,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        """Submit direct analysis (no MinIO storage)"""
        return await self._request(
            "POST",
            "/direct/analyze",
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
                "user_id": user_id,
                "target_column": target_column,
            },
        )
    
    async def quick_stats(
        self,
        csv_content: str,
        is_base64: bool = False,
    ) -> Dict[str, Any]:
        """Get quick stats synchronously"""
        return await self._request(
            "POST",
            "/direct/quick-stats",
            json={
                "csv_content": csv_content,
                "is_base64": is_base64,
            },
        )
