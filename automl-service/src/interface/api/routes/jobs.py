"""
FastAPI Router - Job endpoints (Redis Queue based)
"""

from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException

from ..dependencies import get_container
from ..schemas import ErrorResponse, JobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_job_status(
    job_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Get the status of a training job.

    Poll this endpoint to track job progress.
    """
    container = get_container()

    job_data = container.job_queue.get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Check permission
    if job_data["user_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return JobResponse(
        job_id=job_data["id"],
        job_type=job_data["job_type"],
        status=job_data["status"],
        progress=job_data["progress"],
        status_message=job_data.get("status_message", ""),
        model_id=job_data.get("model_id"),
        result=job_data.get("result"),
        error_message=job_data.get("error_message"),
        created_at=job_data["created_at"],
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
    )


@router.get(
    "",
    response_model=List[JobResponse],
)
async def list_jobs(
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    List all jobs for the current user/session.
    """
    container = get_container()

    jobs = container.job_queue.list_jobs(x_user_id, x_session_id)

    return [
        JobResponse(
            job_id=j["id"],
            job_type=j["job_type"],
            status=j["status"],
            progress=j["progress"],
            status_message=j.get("status_message", ""),
            model_id=j.get("model_id"),
            result=j.get("result"),
            error_message=j.get("error_message"),
            created_at=j["created_at"],
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
        )
        for j in jobs
    ]


@router.post(
    "/{job_id}/cancel",
    response_model=dict,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
)
async def cancel_job(
    job_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Cancel a pending job.

    Note: Running jobs cannot be cancelled.
    """
    container = get_container()

    success = container.job_queue.cancel_job(job_id, x_user_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job (not found, wrong user, or already running)")

    return {"status": "cancelled", "job_id": job_id}


@router.delete(
    "/{job_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
)
async def delete_job(
    job_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Delete a job record.
    """
    container = get_container()

    success = container.job_queue.delete_job(job_id, x_user_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return {"status": "deleted", "job_id": job_id}
