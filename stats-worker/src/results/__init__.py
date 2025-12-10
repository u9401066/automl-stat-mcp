"""
Results Management Module

Provides local storage management for analysis results.

Directory Structure:
    /results/{user_id}/{job_name}_{timestamp}/
        ├── metadata.json          # Job info, data source, parameters
        ├── report.json            # Analysis results in JSON
        ├── report.html            # Human-readable HTML report
        ├── figures/
        │   ├── roc_curve.png
        │   └── ...
        └── data/
            └── source_info.json   # Original dataset metadata
"""

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
