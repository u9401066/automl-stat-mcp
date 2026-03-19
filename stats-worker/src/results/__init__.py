"""
Results Management Module

⚠️ DEPRECATED: This module is deprecated as of the project-oriented architecture refactoring.

All results are now stored in:
- Redis (temp storage with TTL) for job status and quick results
- MinIO (permanent storage) for reports and visualizations

No local file storage is used anymore.

This module is kept for backward compatibility but should not be used in new code.
"""
import warnings

warnings.warn(
    "The results module is deprecated. "
    "Results are now stored in Redis (temp) and MinIO (permanent). "
    "No local file storage is used.",
    DeprecationWarning,
    stacklevel=2
)

from .manager import (
    JobResultsManager,
    JobMetadata,
    SourceInfo,
    DEFAULT_RESULTS_BASE,
)
from .worker_mixin import WorkerResultsMixin

__all__ = [
    "JobResultsManager",
    "JobMetadata",
    "SourceInfo",
    "DEFAULT_RESULTS_BASE",
    "WorkerResultsMixin",
]
