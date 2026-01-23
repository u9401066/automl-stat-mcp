"""
Storage Routes - Redis and MinIO access for MCP result persistence

Provides endpoints for storing and retrieving analysis results:
- Redis: Fast temporary storage with TTL
- MinIO: Persistent file storage
"""
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..infrastructure.redis_client import redis_client
from ..infrastructure.storage_factory import get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/storage", tags=["Storage"])


# =============================================================================
# Redis Storage Models
# =============================================================================

class RedisSetRequest(BaseModel):
    """Request to set a value in Redis"""
    key: str
    value: Dict[str, Any]
    ttl: int = 604800  # 7 days default


class RedisGetResponse(BaseModel):
    """Response from Redis get"""
    key: str
    value: Optional[Dict[str, Any]]
    exists: bool


# =============================================================================
# MinIO Storage Models
# =============================================================================

class MinIOUploadRequest(BaseModel):
    """Request to upload to MinIO"""
    bucket: str
    path: str
    content: str
    content_type: str = "application/json"


class MinIOUploadResponse(BaseModel):
    """Response from MinIO upload"""
    bucket: str
    path: str
    full_path: str
    size: int


# =============================================================================
# Redis Endpoints
# =============================================================================

@router.post("/redis/set", tags=["Redis"])
async def redis_set(request: RedisSetRequest) -> Dict[str, Any]:
    """
    Set a value in Redis with optional TTL.

    Used by MCP tools to store analysis results for quick retrieval.
    """
    try:
        # Serialize the value to JSON
        value_json = json.dumps(request.value, ensure_ascii=False)

        # Store in Redis
        await redis_client.set(
            request.key,
            value_json,
            ex=request.ttl,
        )

        logger.info(f"Stored in Redis: {request.key} (TTL: {request.ttl}s)")

        return {
            "status": "success",
            "key": request.key,
            "ttl": request.ttl,
        }

    except Exception as e:
        logger.error(f"Redis set failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/redis/get", response_model=RedisGetResponse, tags=["Redis"])
async def redis_get(key: str) -> RedisGetResponse:
    """
    Get a value from Redis.

    Returns the stored analysis result if it exists.
    """
    try:
        value_json = await redis_client.get(key)

        if value_json is None:
            return RedisGetResponse(
                key=key,
                value=None,
                exists=False,
            )

        # Parse JSON
        value = json.loads(value_json)

        return RedisGetResponse(
            key=key,
            value=value,
            exists=True,
        )

    except Exception as e:
        logger.error(f"Redis get failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/redis/delete", tags=["Redis"])
async def redis_delete(key: str) -> Dict[str, Any]:
    """Delete a key from Redis"""
    try:
        deleted = await redis_client.delete(key)

        return {
            "status": "success",
            "key": key,
            "deleted": deleted > 0,
        }

    except Exception as e:
        logger.error(f"Redis delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/redis/keys", tags=["Redis"])
async def redis_keys(pattern: str = "stats:result:*", limit: int = 100) -> Dict[str, Any]:
    """
    List keys matching a pattern.

    Used to list analysis results for a user.
    """
    try:
        keys = []
        async for key in redis_client.scan_iter(match=pattern, count=limit):
            keys.append(key)
            if len(keys) >= limit:
                break

        return {
            "status": "success",
            "pattern": pattern,
            "count": len(keys),
            "keys": keys,
        }

    except Exception as e:
        logger.error(f"Redis keys failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# MinIO Endpoints
# =============================================================================

@router.post("/minio/upload", response_model=MinIOUploadResponse, tags=["MinIO"])
async def minio_upload(request: MinIOUploadRequest) -> MinIOUploadResponse:
    """
    Upload content to MinIO.

    Used by MCP tools to persist analysis results permanently.
    """
    try:
        # Upload content
        content_bytes = request.content.encode('utf-8')
        storage = get_storage()

        # Write to storage backend
        full_path = f"{request.bucket}/{request.path}"
        await storage.write_bytes(
            path=full_path,
            data=content_bytes,
            content_type=request.content_type,
        )

        full_path = f"{request.bucket}/{request.path}"
        logger.info(f"Uploaded to MinIO: {full_path}")

        return MinIOUploadResponse(
            bucket=request.bucket,
            path=request.path,
            full_path=full_path,
            size=len(content_bytes),
        )

    except Exception as e:
        logger.error(f"MinIO upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/minio/download", tags=["MinIO"])
async def minio_download(bucket: str, path: str) -> Dict[str, Any]:
    """
    Download content from MinIO.

    Returns the stored analysis result.
    """
    try:
        storage = get_storage()
        full_path = f"{bucket}/{path}"
        content = await storage.read_bytes(full_path)

        # Try to parse as JSON
        try:
            data = json.loads(content.decode('utf-8'))
            return {
                "status": "success",
                "bucket": bucket,
                "path": path,
                "content_type": "application/json",
                "data": data,
            }
        except json.JSONDecodeError:
            # Return as text
            return {
                "status": "success",
                "bucket": bucket,
                "path": path,
                "content_type": "text/plain",
                "content": content.decode('utf-8'),
            }

    except Exception as e:
        logger.error(f"MinIO download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/minio/list", tags=["MinIO"])
async def minio_list(
    bucket: str,
    prefix: str = "",
    limit: int = 100,
) -> Dict[str, Any]:
    """
    List objects in MinIO bucket.

    Used to list analysis results for a user.
    """
    try:
        storage = get_storage()
        dir_path = f"{bucket}/{prefix}" if prefix else bucket
        objects = await storage.list_files(dir_path, recursive=True)

        return {
            "status": "success",
            "bucket": bucket,
            "prefix": prefix,
            "count": len(objects),
            "objects": objects,
        }

    except Exception as e:
        logger.error(f"MinIO list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
