# =============================================================================
# POST-Only API Wrapper
# =============================================================================
#
# This module provides POST-only endpoints that wrap internal GET operations.
# Required for enterprise environments that mandate POST-only external APIs.
#
# Usage:
#   Include this router in your FastAPI app for external-facing deployments.
#
# =============================================================================

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["POST-Only API"])


# =============================================================================
# Request Models (for POST body)
# =============================================================================


class ListDatasetsRequest(BaseModel):
    """Request body for listing datasets"""

    pass  # No parameters needed, user_id comes from header


class GetDatasetRequest(BaseModel):
    """Request body for getting a specific dataset"""

    dataset_id: str


class ListJobsRequest(BaseModel):
    """Request body for listing jobs"""

    pass


class GetJobRequest(BaseModel):
    """Request body for getting job status"""

    job_id: str


class ListModelsRequest(BaseModel):
    """Request body for listing models"""

    pass


class GetModelRequest(BaseModel):
    """Request body for getting model info"""

    model_id: str


class GetLeaderboardRequest(BaseModel):
    """Request body for getting model leaderboard"""

    model_id: str


# =============================================================================
# POST-Only Endpoints
# =============================================================================

# These endpoints wrap the internal GET endpoints with POST interface.
# The actual implementation should import and call the corresponding
# service layer functions directly.

# Note: This is a template. In production, import your actual services:
#
# from src.application.services import (
#     DatasetService, JobService, ModelService
# )
# from src.infrastructure.repositories import (
#     DatasetRepository, JobRepository, ModelRepository
# )


def get_user_id(request: Request) -> str:
    """Extract user ID from request headers"""
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return user_id


@router.post("/datasets/list")
async def list_datasets_post(
    body: ListDatasetsRequest,
    request: Request,
):
    """
    List all datasets (POST wrapper for GET /datasets)

    This endpoint accepts POST requests for enterprise compliance.
    """
    # Import here to avoid circular imports
    from src.interface.api.routes.datasets import list_datasets

    return await list_datasets(request)


@router.post("/datasets/get")
async def get_dataset_post(
    body: GetDatasetRequest,
    request: Request,
):
    """
    Get a specific dataset (POST wrapper for GET /datasets/{id})
    """
    from src.interface.api.routes.datasets import get_dataset

    return await get_dataset(body.dataset_id, request)


@router.post("/jobs/list")
async def list_jobs_post(
    body: ListJobsRequest,
    request: Request,
):
    """
    List all jobs (POST wrapper for GET /jobs)
    """
    from src.interface.api.routes.jobs import list_jobs

    return await list_jobs(request)


@router.post("/jobs/get")
async def get_job_post(
    body: GetJobRequest,
    request: Request,
):
    """
    Get job status (POST wrapper for GET /jobs/{id})
    """
    from src.interface.api.routes.jobs import get_job

    return await get_job(body.job_id, request)


@router.post("/models/list")
async def list_models_post(
    body: ListModelsRequest,
    request: Request,
):
    """
    List all models (POST wrapper for GET /models)
    """
    from src.interface.api.routes.models import list_models

    return await list_models(request)


@router.post("/models/get")
async def get_model_post(
    body: GetModelRequest,
    request: Request,
):
    """
    Get model info (POST wrapper for GET /models/{id})
    """
    from src.interface.api.routes.models import get_model

    return await get_model(body.model_id, request)


@router.post("/models/leaderboard")
async def get_leaderboard_post(
    body: GetLeaderboardRequest,
    request: Request,
):
    """
    Get model leaderboard (POST wrapper for GET /models/{id}/leaderboard)
    """
    from src.interface.api.routes.models import get_leaderboard

    return await get_leaderboard(body.model_id, request)
