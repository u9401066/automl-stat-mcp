"""
Stats Service - Jobs Routes

Common routes for job management.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from typing import Optional

from ..infrastructure.redis_client import redis_client
from ..infrastructure.minio_client import minio_client

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a job.
    
    Returns:
        Job information including status, progress, and result_path when completed.
    """
    job = await redis_client.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    return job


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    """
    Get the result of a completed job.
    
    Returns:
        The JSON result from the analysis.
    """
    job = await redis_client.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job['status']}"
        )
    
    report = minio_client.get_report(job_id)
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found in storage"
        )
    
    return {
        "job_id": job_id,
        "job_type": job.get("job_type"),
        "result": report
    }


@router.get("/{job_id}/html", response_class=HTMLResponse)
async def get_job_html_report(job_id: str):
    """
    Get HTML report for EDA jobs.
    
    Returns the ydata-profiling HTML report for viewing in browser.
    """
    job = await redis_client.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    if job.get("job_type") != "eda":
        raise HTTPException(
            status_code=400,
            detail="HTML reports are only available for EDA jobs"
        )
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job['status']}"
        )
    
    html = minio_client.get_html_report(job_id)
    
    if not html:
        raise HTTPException(
            status_code=404,
            detail="HTML report not found in storage"
        )
    
    return html


@router.get("/")
async def list_jobs(
    user_id: str,
    job_type: Optional[str] = None,
    limit: int = 50
):
    """
    List jobs for a user.
    
    Args:
        user_id: User ID to filter by
        job_type: Optional filter by job type (eda, tableone)
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs sorted by creation time (newest first)
    """
    jobs = await redis_client.list_jobs(
        user_id=user_id,
        job_type=job_type,
        limit=limit
    )
    
    return {
        "jobs": jobs,
        "count": len(jobs),
        "user_id": user_id
    }


@router.delete("/{job_id}")
async def delete_job(job_id: str, user_id: str):
    """
    Delete a job record.
    
    Note: This only removes the job metadata, not the stored reports.
    """
    success = await redis_client.delete_job(job_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or not owned by user"
        )
    
    return {"message": f"Job {job_id} deleted successfully"}
