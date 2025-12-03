"""
Statistics Tools for MCP

Provides statistical analysis capabilities through the Stats Service:
- EDA (Exploratory Data Analysis) reports using ydata-profiling
- Table 1 generation using tableone package
"""
import logging
import time
from typing import Optional, List

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_statistics_tools(mcp: FastMCP, automl_client) -> None:
    """Register statistics tools with MCP server"""
    
    from .stats_client import StatsClient
    stats_client = StatsClient()
    
    @mcp.tool()
    async def submit_eda_job(
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        title: Optional[str] = "EDA Report",
        minimal: Optional[bool] = True,
    ) -> dict:
        """
        📊 Submit an EDA (Exploratory Data Analysis) job.
        
        This generates a comprehensive data profiling report using ydata-profiling.
        The job runs asynchronously - use get_stats_job_status() to check progress.
        
        Args:
            dataset_id: ID of the dataset to analyze (must be registered in AutoML)
            user_id: User ID for isolation
            session_id: Optional session ID
            title: Report title
            minimal: Use minimal mode for faster processing (default: True)
        
        Returns:
            job_id: Job identifier for tracking
            status: "pending"
            message: Status message
            
        Next steps:
            1. Use get_stats_job_status(job_id) to check progress
            2. When completed, use get_eda_result(job_id) to get the report
        """
        return await stats_client.submit_eda_job(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            title=title,
            minimal=minimal,
        )
    
    @mcp.tool()
    async def submit_tableone_job(
        dataset_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        columns: Optional[List[str]] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        groupby: Optional[str] = None,
        nonnormal: Optional[List[str]] = None,
        pval: Optional[bool] = False,
    ) -> dict:
        """
        📋 Submit a Table 1 (summary statistics) job.
        
        Generates a publication-ready Table 1 with descriptive statistics.
        Perfect for research papers and clinical data summaries.
        
        Args:
            dataset_id: ID of the dataset to analyze
            user_id: User ID for isolation
            session_id: Optional session ID
            columns: Columns to include (all if not specified)
            categorical: Columns to treat as categorical
            continuous: Columns to treat as continuous
            groupby: Column to stratify by (e.g., treatment group)
            nonnormal: Columns to report as median/IQR instead of mean/SD
            pval: Include p-values for group comparisons
        
        Returns:
            job_id: Job identifier for tracking
            status: "pending"
            
        Example:
            submit_tableone_job(
                dataset_id="abc123",
                user_id="user1",
                groupby="treatment_group",
                categorical=["gender", "diagnosis"],
                nonnormal=["age", "income"],
                pval=True
            )
        """
        return await stats_client.submit_tableone_job(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            columns=columns,
            categorical=categorical,
            continuous=continuous,
            groupby=groupby,
            nonnormal=nonnormal,
            pval=pval,
        )
    
    @mcp.tool()
    async def get_stats_job_status(
        job_id: str,
    ) -> dict:
        """
        Get the status of a statistics job.
        
        Args:
            job_id: Job ID from submit_eda_job or submit_tableone_job
        
        Returns:
            job_id: Job identifier
            job_type: "eda" or "tableone"
            status: "pending" | "running" | "completed" | "failed"
            progress: 0.0 to 1.0
            message: Human-readable status message
            result_path: (when completed) Path to result in MinIO
            error: (when failed) Error description
        """
        return await stats_client.get_job_status(job_id)
    
    @mcp.tool()
    async def get_stats_job_result(
        job_id: str,
    ) -> dict:
        """
        Get the result of a completed statistics job.
        
        For EDA jobs, returns the ydata-profiling analysis.
        For TableOne jobs, returns the summary statistics table.
        
        Args:
            job_id: Job ID of a completed job
        
        Returns:
            job_id: Job identifier
            job_type: Type of job
            result: The analysis result (structure depends on job_type)
        """
        return await stats_client.get_job_result(job_id)
    
    @mcp.tool()
    async def list_stats_jobs(
        user_id: str,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> dict:
        """
        List statistics jobs for a user.
        
        Args:
            user_id: User ID to filter by
            job_type: Optional filter by type ("eda" or "tableone")
            limit: Maximum number of jobs to return
        
        Returns:
            jobs: List of job records
            count: Number of jobs returned
        """
        return await stats_client.list_jobs(
            user_id=user_id,
            job_type=job_type,
            limit=limit,
        )
    
    @mcp.tool()
    async def get_column_suggestions(
        dataset_id: str,
        user_id: str,
    ) -> dict:
        """
        🔍 Get column type suggestions for TableOne configuration.
        
        Analyzes the dataset and suggests which columns are:
        - Categorical vs Continuous
        - Non-normally distributed (should use median/IQR)
        - Good candidates for groupby stratification
        
        Use this before submit_tableone_job to optimize parameters.
        
        Args:
            dataset_id: Dataset ID to analyze
            user_id: User ID
        
        Returns:
            suggestions:
                categorical: Suggested categorical columns
                continuous: Suggested continuous columns
                nonnormal: Columns with high skewness
                groupby: Good groupby candidates (2-5 unique values)
        """
        return await stats_client.get_column_suggestions(
            dataset_id=dataset_id,
            user_id=user_id,
        )
    
    @mcp.tool()
    async def preview_dataset_stats(
        dataset_id: str,
        n_rows: int = 10,
    ) -> dict:
        """
        Preview a dataset before running statistical analysis.
        
        Returns first N rows and basic information about the dataset.
        
        Args:
            dataset_id: Dataset ID to preview
            n_rows: Number of rows to return (max 100)
        
        Returns:
            shape: {"rows": N, "columns": M}
            columns: List of column names
            dtypes: Column data types
            preview: First N rows as records
            missing_values: Count of missing values per column
        """
        return await stats_client.preview_dataset(
            dataset_id=dataset_id,
            n_rows=n_rows,
        )
    
    @mcp.tool()
    async def run_quick_eda(
        dataset_id: str,
        user_id: str,
        wait_timeout: int = 600,
    ) -> dict:
        """
        🚀 Quick EDA: Submit and wait for EDA report completion.
        
        This is a convenience tool that:
        1. Submits an EDA job
        2. Waits for completion
        3. Returns the full report
        
        ⚠️ This call blocks until the report is ready or times out.
        
        Args:
            dataset_id: Dataset to analyze
            user_id: User ID
            wait_timeout: Maximum seconds to wait (default: 600)
        
        Returns:
            job_id: Job identifier
            status: "completed" | "failed" | "timeout"
            result: (if completed) The EDA report
            error: (if failed) Error message
        """
        # Submit job
        submit_result = await stats_client.submit_eda_job(
            dataset_id=dataset_id,
            user_id=user_id,
            minimal=True,
        )
        
        job_id = submit_result.get("job_id")
        if not job_id:
            return {"status": "failed", "error": "Failed to submit job"}
        
        # Poll for completion
        start_time = time.time()
        poll_interval = 5
        
        while time.time() - start_time < wait_timeout:
            status = await stats_client.get_job_status(job_id)
            
            job_status = status.get("status")
            
            if job_status == "completed":
                result = await stats_client.get_job_result(job_id)
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "result": result.get("result"),
                }
            
            if job_status == "failed":
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": status.get("error"),
                }
            
            time.sleep(poll_interval)
        
        return {
            "job_id": job_id,
            "status": "timeout",
            "message": f"Job did not complete within {wait_timeout} seconds. Check status with get_stats_job_status()",
        }
    
    @mcp.tool()
    async def run_quick_tableone(
        dataset_id: str,
        user_id: str,
        groupby: Optional[str] = None,
        pval: bool = True,
        wait_timeout: int = 300,
    ) -> dict:
        """
        🚀 Quick Table 1: Generate summary statistics with smart defaults.
        
        This is a convenience tool that:
        1. Analyzes columns to determine types
        2. Submits a TableOne job with smart defaults
        3. Waits for completion
        4. Returns the formatted table
        
        ⚠️ This call blocks until the table is ready or times out.
        
        Args:
            dataset_id: Dataset to summarize
            user_id: User ID
            groupby: Column to stratify by (optional)
            pval: Include p-values if grouped (default: True)
            wait_timeout: Maximum seconds to wait (default: 300)
        
        Returns:
            job_id: Job identifier
            status: "completed" | "failed" | "timeout"
            result: (if completed) The Table 1 data
        """
        # Get column suggestions first
        try:
            suggestions = await stats_client.get_column_suggestions(
                dataset_id=dataset_id,
                user_id=user_id,
            )
            categorical = suggestions.get("suggestions", {}).get("categorical", [])
            nonnormal = suggestions.get("suggestions", {}).get("nonnormal", [])
        except Exception:
            categorical = None
            nonnormal = None
        
        # Submit job
        submit_result = await stats_client.submit_tableone_job(
            dataset_id=dataset_id,
            user_id=user_id,
            categorical=categorical,
            nonnormal=nonnormal,
            groupby=groupby,
            pval=pval and groupby is not None,
        )
        
        job_id = submit_result.get("job_id")
        if not job_id:
            return {"status": "failed", "error": "Failed to submit job"}
        
        # Poll for completion
        start_time = time.time()
        poll_interval = 3
        
        while time.time() - start_time < wait_timeout:
            status = await stats_client.get_job_status(job_id)
            
            job_status = status.get("status")
            
            if job_status == "completed":
                result = await stats_client.get_job_result(job_id)
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "result": result.get("result"),
                }
            
            if job_status == "failed":
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": status.get("error"),
                }
            
            time.sleep(poll_interval)
        
        return {
            "job_id": job_id,
            "status": "timeout",
            "message": f"Job did not complete within {wait_timeout} seconds.",
        }
    
    logger.info("Registered 9 statistics tools")
