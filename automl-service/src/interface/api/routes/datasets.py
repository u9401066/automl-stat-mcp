"""
FastAPI Router - Dataset endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header

from .schemas import DatasetResponse, RegisterDatasetRequest, ErrorResponse
from .dependencies import get_container
from ...application.use_cases import RegisterDatasetUseCase, ListDatasetsUseCase
from ...application.dto import RegisterDatasetRequest as RegisterDatasetDTO

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post(
    "/register",
    response_model=DatasetResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def register_dataset(
    request: RegisterDatasetRequest,
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    Register a dataset from MinIO.
    
    The file must already exist in MinIO. This endpoint validates the file
    and registers it for use in training.
    """
    container = get_container()
    
    use_case = RegisterDatasetUseCase(
        dataset_repo=container.dataset_repo,
        file_storage=container.file_storage,
    )
    
    try:
        result = await use_case.execute(
            RegisterDatasetDTO(
                name=request.name,
                minio_path=request.minio_path,
                user_id=x_user_id,
                session_id=x_session_id,
                description=request.description,
            )
        )
        
        return DatasetResponse(
            dataset_id=result.dataset_id,
            name=result.name,
            minio_path=result.minio_path,
            columns=result.columns,
            row_count=result.row_count,
            file_size_bytes=result.file_size_bytes,
            created_at=result.created_at,
            description=result.description,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=List[DatasetResponse],
)
async def list_datasets(
    x_user_id: str = Header(..., description="User ID"),
    x_session_id: Optional[str] = Header(None, description="Session ID"),
):
    """
    List all datasets for the current user/session.
    """
    container = get_container()
    
    use_case = ListDatasetsUseCase(dataset_repo=container.dataset_repo)
    
    results = await use_case.execute(x_user_id, x_session_id)
    
    return [
        DatasetResponse(
            dataset_id=r.dataset_id,
            name=r.name,
            minio_path=r.minio_path,
            columns=r.columns,
            row_count=r.row_count,
            file_size_bytes=r.file_size_bytes,
            created_at=r.created_at,
            description=r.description,
        )
        for r in results
    ]


@router.delete(
    "/{dataset_id}",
    response_model=dict,
    responses={404: {"model": ErrorResponse}},
)
async def delete_dataset(
    dataset_id: str,
    x_user_id: str = Header(..., description="User ID"),
):
    """Delete a dataset."""
    container = get_container()
    
    from ...domain.models import DatasetId
    
    try:
        ds_id = DatasetId.from_string(dataset_id)
        dataset = await container.dataset_repo.get_by_id(ds_id)
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        if not dataset.belongs_to(x_user_id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        await container.dataset_repo.delete(ds_id)
        return {"message": "Dataset deleted successfully"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
