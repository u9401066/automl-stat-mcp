"""
FastAPI Router - Job endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, WebSocket, WebSocketDisconnect
import asyncio

from ..schemas import JobResponse, ErrorResponse
from ..dependencies import get_container
from ....application.use_cases import GetJobStatusUseCase
from ....domain.models import JobId

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
    """
    container = get_container()
    
    use_case = GetJobStatusUseCase(job_repo=container.job_repo)
    
    try:
        result = await use_case.execute(job_id, x_user_id)
        
        return JobResponse(
            job_id=result.job_id,
            job_type=result.job_type,
            status=result.status,
            progress=result.progress,
            status_message=result.status_message,
            model_id=result.model_id,
            error_message=result.error_message,
            created_at=result.created_at,
            started_at=result.started_at,
            completed_at=result.completed_at,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


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
    
    jobs = await container.job_repo.find_by_user(x_user_id, x_session_id)
    
    return [
        JobResponse(
            job_id=str(j.id),
            job_type=j.job_type.value,
            status=j.status.value,
            progress=j.progress,
            status_message=j.status_message,
            model_id=j.model_id,
            error_message=j.error_message,
            created_at=j.created_at.isoformat(),
            started_at=j.started_at.isoformat() if j.started_at else None,
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
        )
        for j in jobs
    ]


@router.delete(
    "/{job_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
)
async def cancel_job(
    job_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """
    Cancel a pending or running job.
    """
    container = get_container()
    
    try:
        job_id_obj = JobId.from_string(job_id)
        job = await container.job_repo.get_by_id(job_id_obj)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.belongs_to(x_user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        if job.is_terminal():
            raise HTTPException(status_code=400, detail="Job already completed")
        
        job.cancel()
        await container.job_repo.update(job)
        
        return {"message": "Job cancelled successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.websocket("/ws/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    
    Connect to receive progress updates for a specific job.
    """
    await websocket.accept()
    
    container = get_container()
    
    try:
        # Verify job exists
        job_id_obj = JobId.from_string(job_id)
        job = await container.job_repo.get_by_id(job_id_obj)
        
        if not job:
            await websocket.send_json({"error": "Job not found"})
            await websocket.close()
            return
        
        # Send initial status
        await websocket.send_json(job.to_dict())
        
        # If job is already complete, close connection
        if job.is_terminal():
            await websocket.close()
            return
        
        # Register callback for updates
        async def send_update(data: dict):
            try:
                await websocket.send_json(data)
            except Exception:
                pass
        
        container.job_worker.register_websocket(job_id, send_update)
        
        try:
            # Keep connection alive until job completes or client disconnects
            while True:
                # Check if job is complete
                job = await container.job_repo.get_by_id(job_id_obj)
                if job and job.is_terminal():
                    await websocket.send_json(job.to_dict())
                    break
                
                # Wait for ping from client or timeout
                try:
                    await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    # Send heartbeat
                    await websocket.send_json({"type": "heartbeat"})
        
        finally:
            container.job_worker.unregister_websocket(job_id)
    
    except WebSocketDisconnect:
        container.job_worker.unregister_websocket(job_id)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
