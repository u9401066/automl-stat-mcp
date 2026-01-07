"""
Visualization Storage Module

Handles saving matplotlib figures to MinIO and generating accessible URLs.

Usage:
    from visualization.storage import save_figure_to_minio

    fig, ax = plt.subplots()
    ax.plot(x, y)

    url = save_figure_to_minio(
        fig=fig,
        user_id="user123",
        job_id="job456",
        filename="roc_curve.png"
    )
    # Returns: "http://minio:9000/stats-reports/user123/job456/roc_curve.png"
"""
import io
import logging
from datetime import timedelta
from typing import Optional

import matplotlib

matplotlib.use('Agg')  # Non-interactive backend for server
import matplotlib.pyplot as plt
from minio import Minio
from minio.error import S3Error

from ..config import (
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_REPORTS_BUCKET,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)

logger = logging.getLogger(__name__)

# Default figure settings
DEFAULT_DPI = 300
DEFAULT_FORMAT = "png"
DEFAULT_FIGSIZE = (8, 6)

# Content types mapping
CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
}


def get_minio_client() -> Minio:
    """Get MinIO client instance."""
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """Ensure the bucket exists, create if not."""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"Created bucket: {bucket_name}")
    except S3Error as e:
        logger.error(f"Failed to create bucket {bucket_name}: {e}")
        raise


def save_figure_to_minio(
    fig: plt.Figure,
    user_id: str,
    job_id: str,
    filename: str,
    dpi: int = DEFAULT_DPI,
    format: str = DEFAULT_FORMAT,
    bucket: Optional[str] = None,
    tight_layout: bool = True,
    transparent: bool = False,
) -> str:
    """
    Save a matplotlib figure to MinIO and return the URL.

    Args:
        fig: Matplotlib figure object
        user_id: User identifier for path organization
        job_id: Job identifier for path organization
        filename: Filename for the saved figure (e.g., "roc_curve.png")
        dpi: Resolution in dots per inch (default: 300 for publication quality)
        format: Image format ('png', 'svg', 'pdf', 'jpg')
        bucket: MinIO bucket name (default: MINIO_REPORTS_BUCKET)
        tight_layout: Apply tight_layout before saving
        transparent: Save with transparent background

    Returns:
        URL string to access the saved figure

    Example:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 4, 9])
        >>> url = save_figure_to_minio(fig, "user1", "job1", "plot.png")
        >>> print(url)
        http://minio:9000/stats-reports/user1/job1/plot.png
    """
    bucket = bucket or MINIO_REPORTS_BUCKET

    # Ensure filename has correct extension
    if not filename.lower().endswith(f".{format}"):
        filename = f"{filename}.{format}"

    # Build object path
    object_path = f"{user_id}/{job_id}/{filename}"

    # Apply tight layout if requested
    if tight_layout:
        try:
            fig.tight_layout()
        except Exception:
            pass  # Some figures don't support tight_layout

    # Save figure to bytes buffer
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format=format,
        dpi=dpi,
        bbox_inches='tight',
        facecolor='white' if not transparent else 'none',
        edgecolor='none',
        transparent=transparent,
    )
    buffer.seek(0)

    # Get content type
    content_type = CONTENT_TYPES.get(format.lower(), "application/octet-stream")

    # Upload to MinIO
    client = get_minio_client()
    ensure_bucket_exists(client, bucket)

    try:
        client.put_object(
            bucket_name=bucket,
            object_name=object_path,
            data=buffer,
            length=buffer.getbuffer().nbytes,
            content_type=content_type,
        )
        logger.info(f"Saved figure to MinIO: {bucket}/{object_path}")
    except S3Error as e:
        logger.error(f"Failed to upload figure: {e}")
        raise
    finally:
        buffer.close()
        plt.close(fig)  # Clean up figure memory

    # Build URL
    url = get_figure_url(bucket, object_path)
    return url


def get_figure_url(
    bucket: str,
    object_path: str,
    presigned: bool = False,
    expires: timedelta = timedelta(hours=24),
) -> str:
    """
    Get URL for a figure stored in MinIO.

    Args:
        bucket: MinIO bucket name
        object_path: Path to the object within the bucket
        presigned: If True, generate a presigned URL with expiration
        expires: Expiration time for presigned URL

    Returns:
        URL string
    """
    if presigned:
        client = get_minio_client()
        try:
            url = client.presigned_get_object(bucket, object_path, expires=expires)
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise
    else:
        # Direct URL (requires bucket to be public or accessed via proxy)
        protocol = "https" if MINIO_SECURE else "http"
        return f"{protocol}://{MINIO_ENDPOINT}/{bucket}/{object_path}"


def save_multiple_figures(
    figures: dict,
    user_id: str,
    job_id: str,
    dpi: int = DEFAULT_DPI,
    format: str = DEFAULT_FORMAT,
    bucket: Optional[str] = None,
) -> dict:
    """
    Save multiple figures to MinIO.

    Args:
        figures: Dictionary mapping filename to (fig, title) tuples
                 e.g., {"roc_curve": (fig1, "ROC Curve"), "pr_curve": (fig2, "PR Curve")}
        user_id: User identifier
        job_id: Job identifier
        dpi: Resolution
        format: Image format
        bucket: MinIO bucket

    Returns:
        Dictionary mapping filenames to URLs

    Example:
        >>> urls = save_multiple_figures(
        ...     {"roc": (fig1, "ROC"), "pr": (fig2, "PR")},
        ...     "user1", "job1"
        ... )
        >>> print(urls)
        {"roc": "http://...", "pr": "http://..."}
    """
    results = {}

    for name, (fig, title) in figures.items():
        filename = f"{name}.{format}"
        try:
            url = save_figure_to_minio(
                fig=fig,
                user_id=user_id,
                job_id=job_id,
                filename=filename,
                dpi=dpi,
                format=format,
                bucket=bucket,
            )
            results[name] = {
                "url": url,
                "title": title,
                "filename": filename,
            }
        except Exception as e:
            logger.error(f"Failed to save figure {name}: {e}")
            results[name] = {
                "url": None,
                "title": title,
                "filename": filename,
                "error": str(e),
            }

    return results
