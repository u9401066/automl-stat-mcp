"""
MCP Handlers

Tool handlers for AutoML MCP server.

Tool Categories:
- Info: list_algorithms, health_check
- Dataset: register_dataset, list_datasets, delete_dataset
- Training: submit_automl_job, submit_specific_job, submit_compare_job
- Job: get_job_status, list_jobs, cancel_job
- Model: list_models, get_model_leaderboard, predict, delete_model
- Direct: direct_ml_analyze, direct_ml_quick_stats, direct_preview_data
- Statistics: auto_analyze, generate_tableone_directly, compare_groups, etc.
- Integrated (NEW): smart_analyze, analyze_medical_study, quick_preview
- Resources (NEW): automl://algorithms, automl://health, automl://help/*
"""

from .automl_handler import AutoMLHandler
from .integrated_tools import register_integrated_tools, resolve_csv_path
from .resources import register_resources

__all__ = [
    "AutoMLHandler",
    "register_integrated_tools",
    "register_resources",
    "resolve_csv_path",
]
