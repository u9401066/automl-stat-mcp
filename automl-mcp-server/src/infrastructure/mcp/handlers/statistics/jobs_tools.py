"""
Jobs Management Tools Module - Statistics Job Queue Operations

This module provides MCP tools for managing asynchronous
statistics jobs (EDA, TableOne, etc.).

Tools:
    - get_stats_job_status: Get job status
    - get_stats_job_result: Get completed job result
    - list_stats_jobs: List user's jobs
"""
from typing import Optional

from .base import logger


def register_jobs_tools(mcp, stats_client):
    """Register all job management MCP tools."""
    
    @mcp.tool()
    async def get_stats_job_status(
        job_id: str,
    ) -> dict:
        """
        Get the status of a statistics job.
        
        Args:
            job_id: Job ID from submit_eda_job or submit_tableone_job
        
        Returns:
            job_id: Job identifier
            job_type: "eda" or "tableone"
            status: "pending" | "running" | "completed" | "failed"
            progress: 0.0 to 1.0
            message: Human-readable status message
            result_path: (when completed) Path to result in MinIO
            error: (when failed) Error description
        """
        return await stats_client.get_job_status(job_id)
    
    @mcp.tool()
    async def get_stats_job_result(
        job_id: str,
    ) -> dict:
        """
        Get the result of a completed statistics job.
        
        For EDA jobs, returns the ydata-profiling analysis.
        For TableOne jobs, returns the summary statistics table.
        
        Args:
            job_id: Job ID of a completed job
        
        Returns:
            job_id: Job identifier
            job_type: Type of job
            result: The analysis result (structure depends on job_type)
        """
        return await stats_client.get_job_result(job_id)
    
    @mcp.tool()
    async def list_stats_jobs(
        user_id: str,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        List statistics jobs for a user.
        
        Args:
            user_id: User ID to filter by
            job_type: Optional filter by type ("eda" or "tableone")
            limit: Maximum number of jobs to return
        
        Returns:
            jobs: List of job records
            count: Number of jobs returned
        """
        return await stats_client.list_jobs(
            user_id=user_id,
            job_type=job_type,
            limit=limit,
        )
    
    logger.info("Jobs management tools registered: 3 tools")
