"""
Job Management Tools for MCP

Tools for managing training jobs (status, list, cancel).
"""
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient


def register_job_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register all job management tools"""

    @mcp.tool()
    async def get_job_status(
        job_id: Annotated[str, Field(description="Job ID to check")],
        user_id: Annotated[str, Field(description="User ID")],
    ) -> Dict[str, Any]:
        """
        Get the status of a training job.
        
        Use this to check if training is complete.
        
        Returns:
            job_id: Job identifier
            status: "pending" | "running" | "completed" | "failed" | "cancelled"
            progress: 0.0 to 1.0
            status_message: Human-readable status
            model_id: (only when completed) ID of the trained model
            error_message: (only when failed) Error description
            
        When status is "completed":
            - Use model_id with get_model_leaderboard() to see results
            - Use model_id with predict() to make predictions
        """
        return await client.get_job_status(job_id, user_id)

    @mcp.tool()
    async def list_jobs(
        user_id: Annotated[str, Field(description="User ID")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all training jobs for the user.
        
        Returns jobs in all states (pending, running, completed, failed).
        """
        return await client.list_jobs(user_id, session_id)

    @mcp.tool()
    async def cancel_job(
        job_id: Annotated[str, Field(description="Job ID to cancel")],
        user_id: Annotated[str, Field(description="User ID")],
    ) -> Dict[str, Any]:
        """
        Cancel a pending or running training job.
        
        Cannot cancel jobs that are already completed or failed.
        """
        return await client.cancel_job(job_id, user_id)
