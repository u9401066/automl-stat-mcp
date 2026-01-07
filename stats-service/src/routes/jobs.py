"""
Stats Service - Jobs Routes (DDD)

Common routes for job management.
Refactored to use Domain-Driven Design with Use Cases.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from ..application.use_cases import GetJobResultUseCase, GetJobStatusUseCase, ListJobsUseCase
from ..infrastructure.minio_client import minio_client
from ..infrastructure.repositories import get_job_repository

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_status_use_case() -> GetJobStatusUseCase:
    return GetJobStatusUseCase(job_repo=get_job_repository())


def _get_result_use_case() -> GetJobResultUseCase:
    return GetJobResultUseCase(job_repo=get_job_repository())


def _get_list_use_case() -> ListJobsUseCase:
    return ListJobsUseCase(job_repo=get_job_repository())


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a job.

    Returns:
        Job information including status, progress, and result_path when completed.
    """
    use_case = _get_status_use_case()
    result = await use_case.execute(job_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return {
        "job_id": result.job_id,
        "job_type": result.job_type,
        "status": result.status,
        "progress": result.progress,
        "message": result.message,
        "result_path": result.result_path,
        "error": result.error,
        "created_at": result.created_at,
        "started_at": result.started_at,
        "completed_at": result.completed_at,
    }


@router.get("/{job_id}/result")
async def get_job_result(job_id: str):
    """
    Get the result of a completed job.

    Returns:
        The JSON result from the analysis.
    """
    use_case = _get_result_use_case()
    result = await use_case.execute(job_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if result.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {result.status}"
        )

    # Try to get result from job itself first
    if result.result:
        return {
            "job_id": job_id,
            "job_type": result.job_type,
            "result": result.result
        }

    # Otherwise load from MinIO
    report = minio_client.get_report(job_id)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found in storage"
        )

    return {
        "job_id": job_id,
        "job_type": result.job_type,
        "result": report
    }


@router.get("/{job_id}/html", response_class=HTMLResponse)
async def get_job_html_report(job_id: str):
    """
    Get HTML report for EDA jobs.

    Returns the ydata-profiling HTML report for viewing in browser.
    """
    use_case = _get_status_use_case()
    result = await use_case.execute(job_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if result.job_type != "eda":
        raise HTTPException(
            status_code=400,
            detail="HTML reports are only available for EDA jobs"
        )

    if result.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {result.status}"
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
        job_type: Optional filter by job type (eda, tableone, auto_analyze)
        limit: Maximum number of jobs to return

    Returns:
        List of jobs sorted by creation time (newest first)
    """
    use_case = _get_list_use_case()
    results = await use_case.execute(
        user_id=user_id,
        job_type=job_type,
        limit=limit,
    )

    return {
        "jobs": [
            {
                "job_id": r.job_id,
                "job_type": r.job_type,
                "status": r.status,
                "progress": r.progress,
                "message": r.message,
                "created_at": r.created_at,
                "completed_at": r.completed_at,
            }
            for r in results
        ],
        "count": len(results),
        "user_id": user_id
    }


@router.delete("/{job_id}")
async def delete_job(job_id: str, user_id: str):
    """
    Delete a job record.

    Note: This only removes the job metadata, not the stored reports.
    """
    from ..domain.models import StatsJobId

    job_repo = get_job_repository()

    try:
        job_id_obj = StatsJobId.from_string(job_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid job ID format"
        ) from None

    # Get job to verify ownership
    job = await job_repo.get_by_id(job_id_obj)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    if not job.belongs_to(user_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    success = await job_repo.delete(job_id_obj)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete job"
        )

    return {"message": f"Job {job_id} deleted successfully"}
