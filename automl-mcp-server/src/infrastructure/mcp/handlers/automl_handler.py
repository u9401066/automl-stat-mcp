"""
AutoML MCP Handler

Unified handler that registers all MCP tools and resources.
Modular design - each tool category in its own file.
"""

import logging

from mcp.server.fastmcp import FastMCP

from ..client import get_client
from .cleaning_tools import register_cleaning_tools
from .dataset_tools import register_dataset_tools
from .direct_tools import register_direct_tools
from .info_tools import register_info_tools
from .integrated_tools import register_integrated_tools
from .job_tools import register_job_tools
from .model_tools import register_model_tools
from .orchestration_tools import register_orchestration_tools
from .power_tools import register_power_tools
from .resources import register_resources
from .smart_tools import register_smart_tools
from .statistics_tools import register_statistics_tools
from .training_tools import register_training_tools
from .upload_tools import register_upload_tools

logger = logging.getLogger(__name__)


class AutoMLHandler:
    """
    Main handler for AutoML MCP tools.

    Tool Categories:
    - Info: list_algorithms, health_check
    - Dataset: register_dataset, list_datasets, delete_dataset
    - Training: submit_automl_job, submit_specific_job, submit_compare_job
    - Job: get_job_status, list_jobs, cancel_job
    - Model: list_models, get_model_leaderboard, predict, delete_model
    - Direct: direct_ml_analyze, direct_ml_quick_stats, direct_preview_data

    🧠 Statistics (Smart Analysis):
    - auto_analyze: Intelligent automatic statistical analysis (RECOMMENDED)
    - run_quick_auto_analyze: One command, complete analysis results
    - get_analysis_capabilities: What auto_analyze can do
    - submit_eda_job, submit_tableone_job: Manual analysis options
    - get_stats_job_status, get_stats_job_result, list_stats_jobs
    - get_column_suggestions, preview_dataset_stats
    - run_quick_eda, run_quick_tableone
    - analyze_csv_directly, get_quick_stats: Direct stats analysis

    🎯 Smart Workflow (guided analysis with tickets):
    - start_data_analysis: Create analysis ticket, guide user decisions
    - execute_analysis_ticket: Execute based on user choice (temp/persistent)
    - check_analysis_progress: Track running analysis jobs

    🚀 Integrated Tools (NEW - Recommended):
    - smart_analyze: Complete analysis in one call (stats + tableone + correlations)
    - analyze_medical_study: Medical study pipeline (baseline + treatment effects)
    - quick_preview: Fast data overview with auto path resolution
    - compare_treatment_groups: Simplified group comparison

    🚀 Smart Orchestration (convenience tools):
    - quick_train: Fastest path from CSV to model
    - train_and_wait: Submit and wait for completion
    - wait_for_job: Wait for any job to complete
    - analyze_dataset: Get recommendations before training
    - get_training_summary: Overview of all resources

    📚 Resources (read-only info):
    - automl://algorithms - Available ML algorithms
    - automl://health - Service health status
    - automl://help/upload - Upload workflow help
    - automl://help/paths - Path resolution guide

    Total: 45+ tools (23 AutoML + 12 Statistics + 4 Integrated + 3 Smart Workflow + 3 Upload)
    """

    def __init__(self, mcp: FastMCP):
        self._mcp = mcp
        self._client = get_client()
        self._register_all_tools()
        self._register_resources()
        logger.info("AutoML Handler initialized with 45+ tools and 4 resources")

    def _register_all_tools(self) -> None:
        """Register all tool categories"""
        register_info_tools(self._mcp, self._client)
        register_dataset_tools(self._mcp, self._client)
        register_upload_tools(self._mcp, self._client)
        register_training_tools(self._mcp, self._client)
        register_job_tools(self._mcp, self._client)
        register_model_tools(self._mcp, self._client)
        register_orchestration_tools(self._mcp, self._client)
        register_direct_tools(self._mcp, self._client)
        register_statistics_tools(self._mcp, self._client)
        register_smart_tools(self._mcp, self._client)
        register_cleaning_tools(self._mcp, self._client)
        register_integrated_tools(self._mcp, self._client)  # Integrated tools
        register_power_tools(self._mcp, self._client)  # Consolidated power tools

    def _register_resources(self) -> None:
        """Register MCP resources (read-only info)"""
        register_resources(self._mcp, self._client)
