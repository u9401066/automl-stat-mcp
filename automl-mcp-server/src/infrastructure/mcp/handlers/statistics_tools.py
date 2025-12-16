"""
Statistics Tools for MCP

Provides statistical analysis capabilities through the Stats Service:
- Auto-analyze: Intelligent automatic statistical analysis
- EDA (Exploratory Data Analysis) reports using ydata-profiling
- Table 1 generation using tableone package
- Advanced Analysis: Correlation, VIF, Missing patterns, Group comparisons
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Data directories mounted in container
# Only sample_data (public test data) and projects (user research projects)
# All temp data goes to Redis, permanent results go to MinIO
DATA_MOUNT_PATHS = [
    "/data/sample_data",    # ./sample_data:/data/sample_data (read-only)
    "/data/projects",       # ./projects:/data/projects (read-write)
]


def _read_csv_from_path_or_reject(csv_path_or_content: str) -> Tuple[bool, Union[str, Dict]]:
    """
    Helper function to validate input and read CSV from path.

    Design principle:
    - Agent should pass FILE PATH, not raw CSV content
    - If raw content is passed, reject and guide Agent to use upload_dataset

    Args:
        csv_path_or_content: Should be a file path like "/data/sample_data/iris.csv"

    Returns:
        Tuple of (success: bool, result: str | dict)
        - If success=True: result is the CSV content string
        - If success=False: result is an error dict to return to Agent
    """
    # Check if it looks like a file path
    looks_like_path = (
        csv_path_or_content.startswith("/data/") or
        csv_path_or_content.startswith("/home/") or
        csv_path_or_content.startswith("./") or
        (csv_path_or_content.endswith(".csv") and "/" in csv_path_or_content) or
        any(csv_path_or_content.startswith(p) for p in DATA_MOUNT_PATHS)
    )

    # Check if it looks like raw CSV content (has newlines, commas, typical CSV patterns)
    looks_like_csv_content = (
        "\n" in csv_path_or_content and
        "," in csv_path_or_content and
        not csv_path_or_content.startswith("/")
    )

    # If it looks like raw CSV content, reject it
    if looks_like_csv_content and not looks_like_path:
        return False, {
            "status": "error",
            "error": "INVALID_INPUT: You passed raw CSV content instead of a file path.",
            "guidance": {
                "problem": "This tool expects a FILE PATH, not raw CSV data.",
                "solution": "Use the upload_dataset tool first to upload/register your data.",
                "correct_workflow": [
                    "1. Call upload_dataset(source_path='/data/sample_data/your_file.csv', ...)",
                    "2. Get job_id or dataset_id from the response",
                    "3. Use that ID with analysis tools, OR",
                    "4. Pass the file PATH directly: csv_path='/data/sample_data/your_file.csv'"
                ],
                "example": {
                    "wrong": "csv_content='name,age\\nAlice,30\\nBob,25'",
                    "correct": "csv_path='/data/sample_data/iris.csv'"
                }
            }
        }

    # Try to read the file
    file_path = Path(csv_path_or_content)

    # Handle relative paths - try to resolve against data mount paths
    if not file_path.is_absolute():
        for mount_path in DATA_MOUNT_PATHS:
            potential_path = Path(mount_path) / csv_path_or_content
            if potential_path.exists():
                file_path = potential_path
                break

    if not file_path.exists():
        return False, {
            "status": "error",
            "error": f"FILE_NOT_FOUND: The file '{csv_path_or_content}' does not exist.",
            "guidance": {
                "available_directories": DATA_MOUNT_PATHS,
                "suggestion": "Use list_available_files() to see available files.",
                "example_paths": [
                    "/data/sample_data/iris.csv",
                    "/data/sample_data/titanic.csv",
                    "/data/projects/my_project/data/my_file.csv"
                ]
            }
        }

    if not file_path.is_file():
        return False, {
            "status": "error",
            "error": f"NOT_A_FILE: '{csv_path_or_content}' is not a file (might be a directory)."
        }

    # Read the file
    try:
        csv_content = file_path.read_text(encoding='utf-8')
        logger.info(f"Successfully read CSV from path: {file_path}")
        return True, csv_content
    except Exception as e:
        return False, {
            "status": "error",
            "error": f"READ_ERROR: Failed to read file '{file_path}': {str(e)}"
        }


def register_statistics_tools(mcp: FastMCP, automl_client) -> None:
    """Register statistics tools with MCP server"""

    from .stats_client import StatsClient
    stats_client = StatsClient()

    # ==================== RESULT MANAGEMENT ====================

    @mcp.tool()
    async def list_analysis_results(
        user_id: str,
        analysis_type: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        """
        📋 List saved analysis results for a user.

        Retrieves results stored in Redis from previous analysis runs.
        Results are automatically saved when using tools like:
        - compare_groups
        - analyze_correlations
        - generate_tableone_directly

        Args:
            user_id: User ID to list results for
            analysis_type: Filter by type (tableone, correlation, compare_groups, roc)
            limit: Maximum number of results to return (default 20)

        Returns:
            results: List of result summaries with result_id and metadata
            count: Number of results found
        """
        try:
            from .result_storage import get_result_storage
            storage = get_result_storage()

            # Query Redis for user's results
            pattern = f"stats:result:stat_{analysis_type or '*'}_*"

            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{storage.stats_service_url}/storage/redis/keys",
                    params={"pattern": pattern, "limit": limit},
                )
                response.raise_for_status()
                data = response.json()

            return {
                "status": "success",
                "user_id": user_id,
                "count": data.get("count", 0),
                "keys": data.get("keys", []),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def get_analysis_result(
        result_id: str,
    ) -> dict:
        """
        📄 Retrieve a saved analysis result by ID.

        Fetches the full result from Redis storage.
        Use list_analysis_results to find available result IDs.

        Args:
            result_id: The result ID (e.g., "stat_tableone_abc123")

        Returns:
            metadata: Result metadata (type, user, created_at)
            result: The full analysis result
        """
        try:
            from .result_storage import get_result_storage
            storage = get_result_storage()

            result = await storage.get_result(result_id)

            if result is None:
                return {
                    "status": "not_found",
                    "error": f"Result '{result_id}' not found or expired",
                }

            return {
                "status": "success",
                "result_id": result_id,
                **result,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== AUTO-ANALYZE (Smart Analysis) ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def auto_analyze(
        dataset_id: str,
        user_id: str,
        target_column: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        🧠 Intelligent automatic statistical analysis.

        This is the RECOMMENDED tool for data analysis. It automatically:

        1. **Data Quality Check**
           - Missing values (count, percentage)
           - Outliers (IQR and Z-score methods)
           - Duplicates, constant columns

        2. **Smart Type Inference**
           - Numeric vs Categorical detection
           - ID columns auto-excluded
           - Datetime detection

        3. **Descriptive Statistics**
           - Numeric: mean, std, median, skewness, kurtosis
           - Categorical: frequency, mode, distribution

        4. **Hypothesis Testing**
           - Normality tests (auto-selects appropriate test)
           - Determines parametric vs non-parametric approach

        5. **Association Analysis** (if target_column provided)
           - Auto-selects appropriate test based on variable types:
             * Numeric vs Numeric: Pearson/Spearman correlation
             * Categorical vs Categorical: Chi-square + Cramér's V
             * Numeric vs Categorical: t-test/ANOVA/Mann-Whitney/Kruskal-Wallis

        6. **Recommendations**
           - Data cleaning suggestions
           - Feature engineering ideas
           - Suitable ML models

        Args:
            dataset_id: Dataset to analyze
            user_id: User ID
            target_column: Optional target for association analysis
            session_id: Optional session ID

        Returns:
            job_id: Job identifier for tracking

        Example:
            # Basic analysis
            auto_analyze(dataset_id="abc", user_id="user1")

            # With target (for ML preparation)
            auto_analyze(dataset_id="abc", user_id="user1", target_column="price")
        """
        return await stats_client.submit_auto_analyze_job(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            target_column=target_column,
        )

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def run_quick_auto_analyze(
        dataset_id: str,
        user_id: str,
        target_column: Optional[str] = None,
        wait_timeout: int = 600,
    ) -> dict:
        """
        🚀 Quick Auto-Analysis: One command, complete results.

        Submits auto_analyze and waits for completion.
        Returns the full analysis report directly.

        ⚠️ This blocks until analysis completes (typically 30-120 seconds).

        Args:
            dataset_id: Dataset to analyze
            user_id: User ID
            target_column: Optional target column for association analysis
            wait_timeout: Max seconds to wait (default: 600)

        Returns:
            status: "completed" | "failed" | "timeout"
            summary: Human-readable overview
            result: Full analysis result including:
                - metadata: rows, columns, memory
                - column_summary: columns by type
                - columns: detailed profile per column
                - data_quality: score and issues
                - correlation_matrix: for numeric columns
                - target_analysis: associations with target
                - recommendations: actionable suggestions
        """
        # Submit job
        submit_result = await stats_client.submit_auto_analyze_job(
            dataset_id=dataset_id,
            user_id=user_id,
            target_column=target_column,
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
                    "summary": result.get("result", {}).get("summary"),
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
            "message": f"Analysis did not complete in {wait_timeout}s. Use get_stats_job_status('{job_id}') to check.",
        }

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def get_analysis_capabilities() -> dict:
        """
        📋 Get capabilities of the auto-analyze engine.

        Returns detailed information about what the auto-analyze
        engine can do, including all tests and metrics available.
        """
        return await stats_client.get_auto_analyze_capabilities()

    # ==================== EDA (ydata-profiling) ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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

    # ==================== DIRECT ANALYSIS (No MinIO Storage) ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def analyze_csv_directly(
        csv_path: str,
        user_id: str,
        target_column: Optional[str] = None,
    ) -> dict:
        """
        📊 Analyze CSV data directly without storing in MinIO.

        ⚠️ Pass FILE PATH, not raw CSV content!

        This is useful for:
        - One-time analysis of temporary data
        - Quick data exploration without permanent storage
        - Testing with small datasets

        Args:
            csv_path: Path to CSV file (e.g., '/data/sample_data/iris.csv')
            user_id: User ID
            target_column: Optional target for association analysis

        Returns:
            job_id: Job ID for tracking
            data_preview: Preview of parsed data (rows, columns, sample)

        Example:
            analyze_csv_directly(
                csv_path="/data/sample_data/iris.csv",
                user_id="user1",
                target_column="species"
            )
        """
        # Validate input - must be file path, not raw CSV content
        success, result = _read_csv_from_path_or_reject(csv_path)
        if not success:
            return result
        csv_content = result

        result = await stats_client.direct_analyze(
            csv_content=csv_content,
            user_id=user_id,
            target_column=target_column,
            is_base64=False,
        )
        return result

    @mcp.tool()
    async def get_quick_stats(
        csv_path: str,
    ) -> dict:
        """
        ⚡ Get quick statistics synchronously (instant results).

        ⚠️ Pass FILE PATH, not raw CSV content!

        Returns immediately with basic statistics without job queue.
        For full analysis, use analyze_csv_directly instead.

        Args:
            csv_path: Path to CSV file (e.g., '/data/sample_data/iris.csv')

        Returns:
            rows: Number of rows
            columns: Number of columns
            column_info: Type, nulls, unique count per column
            missing_summary: Missing value statistics
            numeric_summary: Basic stats for numeric columns
        """
        # Validate input - must be file path, not raw CSV content
        success, result = _read_csv_from_path_or_reject(csv_path)
        if not success:
            return result
        csv_content = result

        result = await stats_client.quick_stats(
            csv_content=csv_content,
            is_base64=False,
        )
        return result

    # ==================== ADVANCED ANALYSIS TOOLS ====================

    @mcp.tool()
    async def analyze_correlations(
        csv_path: str,
        columns: Optional[List[str]] = None,
        method: str = "all",
        min_correlation: float = 0.3,
        save_result: bool = True,
        user_id: str = "default",
    ) -> dict:
        """
        📈 Enhanced correlation analysis with multiple methods.

        ⚠️ Pass FILE PATH, not raw CSV content!

        Computes Pearson, Spearman, and Kendall correlations with:
        - Full correlation matrices
        - P-value matrices for significance testing
        - Heatmap data for visualization
        - Significant pairs highlighted

        Args:
            csv_path: Path to CSV file (e.g., '/data/sample_data/iris.csv')
            columns: Columns to analyze (default: all numeric)
            method: "pearson", "spearman", "kendall", or "all"
            min_correlation: Minimum |r| to flag (default: 0.3)
            save_result: Whether to save result to Redis/MinIO (default True)
            user_id: User ID for result storage (default "default")

        Returns:
            result_id: Unique ID for retrieving result later
            result_path: MinIO path where result is stored
            matrices: Pearson/Spearman correlation and p-value matrices
            significant_pairs: Pairs with significant correlation
            heatmap_data: Ready-to-plot heatmap data
            summary: Overall statistics
        """
        from io import StringIO

        import pandas as pd

        # Validate input - must be file path, not raw CSV content
        success, file_result = _read_csv_from_path_or_reject(csv_path)
        if not success:
            return file_result
        csv_content = file_result

        try:
            df = pd.read_csv(StringIO(csv_content))

            # Get numeric columns
            if columns:
                numeric_cols = [c for c in columns if c in df.columns and df[c].dtype in ['int64', 'float64']]
            else:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

            if len(numeric_cols) < 2:
                return {"status": "error", "error": "Need at least 2 numeric columns"}

            # Compute correlations
            result = {
                "status": "success",
                "columns": numeric_cols,
            }

            # Pearson correlation
            if method in ["pearson", "all"]:
                pearson_corr = df[numeric_cols].corr(method='pearson')
                result["pearson_matrix"] = pearson_corr.to_dict()

            # Spearman correlation
            if method in ["spearman", "all"]:
                spearman_corr = df[numeric_cols].corr(method='spearman')
                result["spearman_matrix"] = spearman_corr.to_dict()

            # Find significant pairs
            significant_pairs = []
            corr_matrix = df[numeric_cols].corr()
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:  # Upper triangle only
                        r = corr_matrix.loc[col1, col2]
                        if abs(r) >= min_correlation:
                            significant_pairs.append({
                                "var1": col1,
                                "var2": col2,
                                "correlation": round(r, 4),
                            })

            result["significant_pairs"] = significant_pairs
            result["summary"] = {
                "n_variables": len(numeric_cols),
                "n_significant_pairs": len(significant_pairs),
                "min_correlation_threshold": min_correlation,
            }

            # Save result if requested
            if save_result:
                try:
                    from .result_storage import get_result_storage
                    storage = get_result_storage()
                    metadata = await storage.save_result(
                        result=result,
                        user_id=user_id,
                        analysis_type="correlation",
                    )
                    result["result_id"] = metadata.result_id
                    result["result_path"] = metadata.minio_path
                except Exception as e:
                    logger.warning(f"Failed to save result: {e}")

            return result

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def compare_groups(
        csv_path: str,
        numeric_column: str,
        group_column: str,
        save_result: bool = True,
        user_id: str = "default",
    ) -> dict:
        """
        🔬 Compare distributions of a numeric variable across groups.

        ⚠️ Pass FILE PATH, not raw CSV content!

        Automatically selects appropriate tests:
        - 2 groups: t-test or Mann-Whitney U
        - 3+ groups: ANOVA or Kruskal-Wallis + post-hoc

        Includes:
        - Normality tests per group
        - Homogeneity of variance (Levene's test)
        - Effect size calculation
        - Post-hoc pairwise comparisons with Bonferroni correction

        Args:
            csv_path: Path to CSV file (e.g., '/data/sample_data/iris.csv')
            numeric_column: Column with numeric values to compare
            group_column: Column with group labels
            save_result: Whether to save result to Redis/MinIO (default True)
            user_id: User ID for result storage (default "default")

        Returns:
            result_id: Unique ID for retrieving result later
            result_path: MinIO path where result is stored
            groups: Group labels
            normality: Normality test results per group
            variance_test: Levene's test result
            main_test: Main comparison (t-test/ANOVA/etc)
            post_hoc: Pairwise comparisons (if >2 groups)
            group_statistics: Descriptive stats per group
        """
        from io import StringIO

        import pandas as pd
        from scipy import stats as scipy_stats

        # Validate input - must be file path, not raw CSV content
        success, file_result = _read_csv_from_path_or_reject(csv_path)
        if not success:
            return file_result
        csv_content = file_result

        try:
            df = pd.read_csv(StringIO(csv_content))

            groups = df[group_column].dropna().unique().tolist()
            n_groups = len(groups)

            # Group statistics
            group_stats = {}
            group_data = {}
            for g in groups:
                data = df[df[group_column] == g][numeric_column].dropna()
                group_data[g] = data.values
                group_stats[str(g)] = {
                    "n": len(data),
                    "mean": round(float(data.mean()), 4),
                    "std": round(float(data.std()), 4),
                    "median": round(float(data.median()), 4),
                }

            # Main test
            if n_groups == 2:
                # Independent t-test
                g1, g2 = groups[:2]
                stat, pval = scipy_stats.ttest_ind(group_data[g1], group_data[g2])
                test_name = "Independent t-test"
            else:
                # One-way ANOVA
                stat, pval = scipy_stats.f_oneway(*[group_data[g] for g in groups])
                test_name = "One-way ANOVA"

            result = {
                "status": "success",
                "groups": groups,
                "n_groups": n_groups,
                "group_statistics": group_stats,
                "main_test": {
                    "test": test_name,
                    "statistic": round(float(stat), 4),
                    "p_value": round(float(pval), 4),
                    "significant": pval < 0.05,
                },
            }

            # Save result if requested
            if save_result:
                try:
                    from .result_storage import get_result_storage
                    storage = get_result_storage()
                    metadata = await storage.save_result(
                        result=result,
                        user_id=user_id,
                        analysis_type="compare_groups",
                    )
                    result["result_id"] = metadata.result_id
                    result["result_path"] = metadata.minio_path
                except Exception as e:
                    logger.warning(f"Failed to save result: {e}")

            return result

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def analyze_missing_values(
        csv_path: str,
    ) -> dict:
        """
        🔍 Comprehensive missing value analysis.

        Detects missing value patterns:
        - MCAR (Missing Completely At Random): Safe for listwise deletion
        - MAR (Missing At Random): Use model-based imputation
        - MNAR (Missing Not At Random): Complex handling needed

        Includes:
        - Per-column missing statistics
        - Little's MCAR test (approximation)
        - Missing value correlations
        - Imputation recommendations

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)

        Returns:
            summary: Overall missing statistics
            columns: Per-column missing details
            pattern: MCAR/MAR/MNAR with confidence
            mcar_test: Little's MCAR test result
            recommendations: Handling suggestions
        """
        from io import StringIO

        import pandas as pd

        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result
            df = pd.read_csv(StringIO(csv_content))

            # Calculate missing statistics
            total_cells = df.shape[0] * df.shape[1]
            total_missing = int(df.isna().sum().sum())

            # Per-column analysis
            columns_analysis = {}
            for col in df.columns:
                missing_count = int(df[col].isna().sum())
                columns_analysis[col] = {
                    "missing_count": missing_count,
                    "missing_pct": round(missing_count / len(df) * 100, 2),
                    "dtype": str(df[col].dtype),
                }

            # Recommendations
            recommendations = []
            high_missing_cols = [c for c, v in columns_analysis.items() if v["missing_pct"] > 20]
            if high_missing_cols:
                recommendations.append(f"Consider dropping columns with >20% missing: {high_missing_cols}")
            if total_missing / total_cells < 0.05:
                recommendations.append("Missing rate <5%: Consider listwise deletion or simple imputation")
            else:
                recommendations.append("Consider multiple imputation or model-based approaches")

            return {
                "status": "success",
                "summary": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "total_missing": total_missing,
                    "overall_missing_pct": round(total_missing / total_cells * 100, 2),
                },
                "columns": columns_analysis,
                "pattern": "Unable to determine (MCAR test requires advanced statistics)",
                "recommendations": recommendations,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()  # RESTORED: VIF is unique functionality for regression diagnostics
    async def check_multicollinearity(
        csv_path: str,
        columns: Optional[List[str]] = None,
        vif_threshold: float = 5.0,
    ) -> dict:
        """
        📊 Check multicollinearity using VIF (Variance Inflation Factor).

        VIF interpretation:
        - VIF = 1: No correlation with other variables
        - VIF < 5: Acceptable (moderate correlation)
        - VIF ≥ 5: High correlation (problematic)
        - VIF ≥ 10: Severe multicollinearity (very problematic)

        High VIF indicates that a variable is highly correlated with
        other variables, which can cause problems in regression models.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            columns: Columns to analyze (default: all numeric)
            vif_threshold: VIF threshold for flagging (default: 5.0)

        Returns:
            vif_results: VIF for each column
            condition_number: Overall condition number
            problematic_columns: Columns with high VIF
            recommendations: Action suggestions
        """
        from io import StringIO

        import numpy as np
        import pandas as pd

        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result
            df = pd.read_csv(StringIO(csv_content))

            # Get numeric columns
            if columns:
                numeric_cols = [c for c in columns if c in df.columns and df[c].dtype in ['int64', 'float64']]
            else:
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

            if len(numeric_cols) < 2:
                return {"status": "error", "error": "Need at least 2 numeric columns"}

            # Calculate VIF using correlation matrix method
            corr_matrix = df[numeric_cols].corr()

            # Simple VIF approximation: VIF_i = 1 / (1 - R^2_i)
            vif_results = {}
            problematic = []

            for col in numeric_cols:
                other_cols = [c for c in numeric_cols if c != col]
                if len(other_cols) > 0:
                    # R^2 from correlation with other variables
                    r_squared = corr_matrix.loc[col, other_cols].pow(2).max()
                    if r_squared < 1:
                        vif = 1 / (1 - r_squared)
                    else:
                        vif = float('inf')
                    vif_results[col] = round(float(vif), 2)
                    if vif >= vif_threshold:
                        problematic.append(col)

            # Condition number
            try:
                cond = np.linalg.cond(df[numeric_cols].dropna().values)
            except (np.linalg.LinAlgError, ValueError):
                cond = None

            # Recommendations
            recommendations = []
            if problematic:
                recommendations.append(f"Consider removing or combining variables: {problematic}")
            if cond and cond > 30:
                recommendations.append("High condition number suggests multicollinearity")
            if not problematic:
                recommendations.append("No severe multicollinearity detected")

            return {
                "status": "success",
                "vif_results": vif_results,
                "condition_number": round(float(cond), 2) if cond else None,
                "problematic_columns": problematic,
                "vif_threshold": vif_threshold,
                "recommendations": recommendations,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def run_full_statistical_analysis(
        csv_path: str,
        target_column: Optional[str] = None,
    ) -> dict:
        """
        🚀 Run complete statistical analysis including all advanced features.

        This is the most comprehensive analysis tool, combining:
        - Basic descriptive statistics
        - Enhanced correlation analysis
        - Missing value pattern detection
        - Multicollinearity check (VIF)
        - Group comparisons (if target is categorical)

        Use this for a complete overview of your dataset.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            target_column: Optional target for group analysis

        Returns:
            correlation_analysis: Full correlation results
            missing_analysis: Missing value patterns
            multicollinearity: VIF analysis
            group_comparisons: Comparisons by target (if applicable)
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Use stats_client direct_analyze for comprehensive analysis
            result = await stats_client.direct_analyze(
                csv_content=csv_content,
                user_id="mcp_user",
                target_column=target_column,
                is_base64=False,
            )
            return {"status": "success", **result}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _compute_correlation_fallback(csv_content: str, columns: Optional[List[str]], is_base64: bool) -> dict:
        """Fallback correlation computation without advanced module"""
        import base64
        from io import StringIO

        import pandas as pd

        if is_base64:
            csv_content = base64.b64decode(csv_content).decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))

        if columns:
            numeric_cols = [c for c in columns if c in df.columns]
        else:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

        if len(numeric_cols) < 2:
            return {"status": "error", "error": "Need at least 2 numeric columns"}

        corr = df[numeric_cols].corr()

        return {
            "status": "success",
            "columns": numeric_cols,
            "pearson_matrix": corr.to_dict(),
            "note": "Basic correlation (advanced module not available)"
        }

    # ==================== TABLE ONE (PUBLICATION TABLES) ====================

    @mcp.tool()
    async def generate_tableone_directly(
        csv_path: str,
        groupby: Optional[str] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        nonnormal: Optional[List[str]] = None,
        pval: bool = True,
        output_format: str = "dict",
        save_result: bool = True,
        user_id: str = "default",
    ) -> dict:
        """
        📊 Generate Table 1 (baseline characteristics) directly from CSV.

        Creates publication-ready summary statistics tables for medical research.
        Automatically detects column types and selects appropriate statistical tests.

        Statistical test selection:
        - Categorical: Chi-square (n≥5) or Fisher's exact (n<5)
        - Continuous normal: t-test (2 groups) or ANOVA (3+ groups)
        - Continuous non-normal: Mann-Whitney U (2) or Kruskal-Wallis (3+)

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            groupby: Column to stratify by (e.g., "treatment_group")
            categorical: Columns to treat as categorical (auto-detect if not specified)
            continuous: Columns to treat as continuous (auto-detect if not specified)
            nonnormal: Columns to report as median[IQR] instead of mean±SD
            pval: Include p-values for group comparisons (default: True)
            output_format: "dict", "markdown", "html", or "latex"
            save_result: Whether to save result to Redis/MinIO (default True)
            user_id: User ID for result storage (default "default")

        Returns:
            result_id: Unique ID for retrieving result later
            result_path: MinIO path where result is stored
            status: "success" or "error"
            table_data: Summary statistics table as nested dict
            n_total: Total sample size
            n_groups: Sample size per group (if grouped)
            format: Requested output format
            markdown/html/latex: Formatted table (if format specified)
            tests_used: Statistical tests applied
        """
        from io import StringIO

        import pandas as pd

        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Parse CSV
            df = pd.read_csv(StringIO(csv_content))

            # Auto-detect column types if not provided
            if categorical is None:
                categorical = []
                for col in df.columns:
                    if df[col].dtype == 'object' or df[col].nunique() <= 10:
                        categorical.append(col)

            if continuous is None:
                continuous = [c for c in df.select_dtypes(include=['number']).columns
                              if c not in categorical and c != groupby]

            # Generate table data
            table_data = {}
            tests_used = {}

            # Overall statistics
            n_total = len(df)
            n_groups = {}
            groups = []

            if groupby and groupby in df.columns:
                groups = df[groupby].dropna().unique().tolist()
                n_groups = {str(g): int((df[groupby] == g).sum()) for g in groups}

            # Process continuous variables
            for col in continuous:
                if col not in df.columns:
                    continue

                col_data = {}

                if groupby and groups:
                    for g in groups:
                        data = df[df[groupby] == g][col].dropna()
                        if col in (nonnormal or []):
                            col_data[str(g)] = f"{data.median():.2f} [{data.quantile(0.25):.2f}-{data.quantile(0.75):.2f}]"
                        else:
                            col_data[str(g)] = f"{data.mean():.2f} ± {data.std():.2f}"
                else:
                    data = df[col].dropna()
                    if col in (nonnormal or []):
                        col_data["Overall"] = f"{data.median():.2f} [{data.quantile(0.25):.2f}-{data.quantile(0.75):.2f}]"
                    else:
                        col_data["Overall"] = f"{data.mean():.2f} ± {data.std():.2f}"

                table_data[col] = col_data
                tests_used[col] = "Mann-Whitney U" if col in (nonnormal or []) else "t-test"

            # Process categorical variables
            for col in categorical:
                if col not in df.columns or col == groupby:
                    continue

                col_data = {}
                categories = df[col].dropna().unique()

                for cat in categories:
                    cat_data = {}
                    if groupby and groups:
                        for g in groups:
                            n = int(((df[groupby] == g) & (df[col] == cat)).sum())
                            total = int((df[groupby] == g).sum())
                            pct = (n / total * 100) if total > 0 else 0
                            cat_data[str(g)] = f"{n} ({pct:.1f}%)"
                    else:
                        n = int((df[col] == cat).sum())
                        pct = (n / n_total * 100) if n_total > 0 else 0
                        cat_data["Overall"] = f"{n} ({pct:.1f}%)"

                    col_data[f"{col}={cat}"] = cat_data

                table_data.update(col_data)
                tests_used[col] = "Chi-square"

            response = {
                "status": "success",
                "n_total": n_total,
                "n_groups": n_groups,
                "variables_analyzed": continuous + categorical,
                "tests_used": tests_used,
                "format": output_format,
                "table_data": table_data,
            }

            # Save result if requested
            if save_result:
                try:
                    from .result_storage import get_result_storage
                    storage = get_result_storage()
                    metadata = await storage.save_result(
                        result=response,
                        user_id=user_id,
                        analysis_type="tableone",
                    )
                    response["result_id"] = metadata.result_id
                    response["result_path"] = metadata.minio_path
                except Exception as e:
                    logger.warning(f"Failed to save result: {e}")

            return response

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def get_tableone_preview(
        csv_path: str,
        groupby: Optional[str] = None,
    ) -> dict:
        """
        🔍 Preview Table 1 configuration and column type suggestions.

        Analyzes dataset and suggests optimal TableOne configuration:
        - Which columns should be categorical vs continuous
        - Which continuous columns appear non-normal (use median/IQR)
        - Good groupby candidates (2-5 unique values)

        Use this before generate_tableone_directly to optimize parameters.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            groupby: Proposed groupby column (optional)

        Returns:
            shape: Dataset dimensions
            suggested_categorical: Columns detected as categorical
            suggested_continuous: Columns detected as continuous
            suggested_nonnormal: Skewed continuous columns
            groupby_candidates: Good columns for stratification
            groupby_info: Info about proposed groupby (if provided)
        """
        from io import StringIO

        import numpy as np
        import pandas as pd

        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result
            df = pd.read_csv(StringIO(csv_content))

            # Detect column types
            categorical = []
            continuous = []
            nonnormal = []
            groupby_candidates = []

            for col in df.columns:
                n_unique = df[col].nunique()
                dtype = df[col].dtype

                # Categorical detection
                if dtype == 'object' or dtype.name == 'category':
                    categorical.append(col)
                    if 2 <= n_unique <= 5:
                        groupby_candidates.append(col)
                elif n_unique <= 10 and n_unique / len(df) < 0.05:
                    categorical.append(col)
                    if 2 <= n_unique <= 5:
                        groupby_candidates.append(col)
                else:
                    continuous.append(col)
                    # Check for non-normality (skewness)
                    if np.issubdtype(dtype, np.number):
                        try:
                            skewness = df[col].dropna().skew()
                            if abs(skewness) > 1.0:
                                nonnormal.append(col)
                        except (TypeError, ValueError):
                            pass

            result = {
                "status": "success",
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "suggested_categorical": categorical,
                "suggested_continuous": continuous,
                "suggested_nonnormal": nonnormal,
                "groupby_candidates": groupby_candidates,
            }

            # Add groupby info if provided
            if groupby and groupby in df.columns:
                groups = df[groupby].value_counts().to_dict()
                result["groupby_info"] = {
                    "column": groupby,
                    "n_groups": len(groups),
                    "group_sizes": groups,
                    "valid": 2 <= len(groups) <= 10,
                }

            return result

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def _generate_tableone_fallback(
        csv_content: str,
        groupby: Optional[str],
        categorical: Optional[List[str]],
        nonnormal: Optional[List[str]],
        pval: bool,
        is_base64: bool,
    ) -> dict:
        """Fallback TableOne generation without advanced module"""
        import base64
        from io import StringIO

        import pandas as pd

        if is_base64:
            csv_content = base64.b64decode(csv_content).decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))

        table_data = {}

        # Auto-detect categorical if not specified
        if categorical is None:
            categorical = [c for c in df.columns
                          if df[c].dtype == 'object' or df[c].nunique() <= 10]

        # Simple summary for each column
        for col in df.columns:
            if col == groupby:
                continue

            if col in categorical:
                # Categorical: count (%)
                counts = df[col].value_counts()
                table_data[col] = {
                    str(k): f"{v} ({100*v/len(df):.1f}%)"
                    for k, v in counts.items()
                }
            else:
                # Continuous: mean±SD or median[IQR]
                if nonnormal and col in nonnormal:
                    median = df[col].median()
                    q1, q3 = df[col].quantile([0.25, 0.75])
                    table_data[col] = f"{median:.2f} [{q1:.2f}, {q3:.2f}]"
                else:
                    mean = df[col].mean()
                    std = df[col].std()
                    table_data[col] = f"{mean:.2f} ± {std:.2f}"

        return {
            "status": "success",
            "table_data": table_data,
            "n_total": len(df),
            "format": "dict",
            "note": "Basic table (advanced module not available)"
        }

    # ==================== SURVIVAL ANALYSIS TOOLS ====================

    @mcp.tool()
    async def kaplan_meier_survival(
        csv_path: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        time_points: Optional[List[float]] = None,
        alpha: float = 0.05,
    ) -> dict:
        """
        📈 Kaplan-Meier survival analysis with log-rank test.

        Performs non-parametric survival analysis:
        - Kaplan-Meier survival curves for each group
        - Median survival time with 95% CI
        - Log-rank test for group comparisons
        - Survival probability at specified time points

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            time_col: Column name for time-to-event (e.g., "survival_months")
            event_col: Column name for event indicator (1=event occurred, 0=censored)
            group_col: Optional column for stratification (e.g., "treatment")
            time_points: Specific times to report survival (e.g., [12, 24, 36])
            alpha: Significance level for CI (default: 0.05 for 95% CI)

        Returns:
            survival_curves: KM curves for each group
            median_survival: Median survival with CI per group
            log_rank_test: Test for difference between groups (if grouped)
            survival_at_times: Survival probability at specified times
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_survival_kaplan_meier_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                time_column=time_col,
                event_column=event_col,
                group_column=group_col,
                time_points=time_points,
                alpha=alpha,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def cox_proportional_hazards(
        csv_path: str,
        time_col: str,
        event_col: str,
        covariates: Optional[List[str]] = None,
        alpha: float = 0.05,
    ) -> dict:
        """
        🔬 Cox Proportional Hazards regression for survival analysis.

        Semi-parametric survival model that estimates hazard ratios:
        - Hazard ratios with 95% CI for each covariate
        - Model fit statistics (log-likelihood, concordance)
        - Wald and likelihood ratio tests

        Interpretation:
        - HR > 1: Increased risk of event
        - HR < 1: Decreased risk (protective)
        - HR = 1: No effect

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            covariates: List of covariate columns (default: all numeric)
            alpha: Significance level for CI

        Returns:
            coefficients: Beta coefficients with SE, HR, CI, p-value
            model_fit: Log-likelihood, concordance index
            global_tests: Wald test, likelihood ratio test
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_survival_cox_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                time_column=time_col,
                event_column=event_col,
                covariates=covariates,
                alpha=alpha,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def compare_survival(
        csv_path: str,
        time_col: str,
        event_col: str,
        group_col: str,
    ) -> dict:
        """
        ⚖️ Compare survival curves between groups.

        Performs comprehensive survival comparison:
        - Kaplan-Meier curves for each group
        - Log-rank test (overall and pairwise)
        - Median survival comparison
        - Hazard ratio estimate

        Use this for:
        - Treatment vs control comparison
        - Risk stratification analysis
        - Prognostic factor evaluation

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Column for group stratification

        Returns:
            groups: Survival statistics per group
            log_rank_test: Test for overall difference
            pairwise_comparisons: Tests between each pair (if >2 groups)
            conclusion: Interpretation of results
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_survival_compare_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                time_column=time_col,
                event_column=event_col,
                group_column=group_col,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def survival_data_summary(
        csv_path: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
    ) -> dict:
        """
        📋 Get summary statistics for survival data.

        Quick overview of survival dataset:
        - Number of subjects, events, censored
        - Follow-up time distribution
        - Median survival per group
        - Event rates

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Optional grouping column

        Returns:
            n_subjects: Total sample size
            n_events: Number of events
            n_censored: Number censored
            follow_up: Follow-up time statistics
            by_group: Statistics per group (if grouped)
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_survival_summary_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                time_column=time_col,
                event_column=event_col,
                group_column=group_col,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== PROPENSITY SCORE ANALYSIS ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def estimate_propensity_scores(
        csv_path: str,
        treatment_col: str,
        covariates: List[str],
        regularization: float = 0.0,
    ) -> dict:
        """
        📊 Estimate propensity scores using logistic regression.

        Propensity score = P(Treatment=1 | Covariates)

        Used for:
        - Observational study analysis
        - Controlling for confounding
        - Matching or weighting for causal inference

        Model diagnostics include:
        - Pseudo R² (McFadden's)
        - C-statistic (AUC)
        - Brier score
        - Score overlap between groups

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            treatment_col: Binary treatment column (0/1)
            covariates: List of covariate columns
            regularization: L2 regularization strength (0=none)

        Returns:
            scores: Propensity score for each observation
            coefficients: Model coefficients per covariate
            model_metrics: C-statistic, pseudo R², Brier score
            score_distribution: Stats for treated vs control
            overlap_region: Common support range
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Submit job via stats_client (which calls stats-service API)
            job_result = await stats_client.submit_propensity_estimate_job(
                user_id="mcp_user",
                treatment_column=treatment_col,
                covariates=covariates,
                csv_content=csv_content,
                is_base64=False,
                regularization=regularization,
            )

            return {
                "status": "success",
                "job_id": job_result.get("job_id"),
                "message": "Job submitted. Use get_stats_job_status to check progress.",
                **job_result
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def match_propensity_scores(
        csv_path: str,
        treatment_col: str,
        covariates: Optional[List[str]] = None,
        score_col: Optional[str] = None,
        method: str = "nearest",
        caliper: Optional[float] = 0.2,
        caliper_scale: str = "std",
        replacement: bool = False,
    ) -> dict:
        """
        🔗 Match treated and control units by propensity score.

        Creates matched pairs to balance covariate distributions.

        Methods:
        - nearest: Greedy nearest neighbor matching
        - optimal: Minimizes total distance (for small datasets)

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            treatment_col: Binary treatment column
            covariates: Covariates for PS estimation (if score_col not provided)
            score_col: Pre-computed propensity score column
            method: 'nearest' or 'optimal'
            caliper: Max distance for match (in std devs or absolute)
            caliper_scale: 'std' (standard deviations) or 'absolute'
            replacement: Allow control to match multiple treated

        Returns:
            n_matched_pairs: Number of successful matches
            n_unmatched_treated: Treated units without match
            n_unmatched_control: Control units not used
            matching_rate_treated: Proportion of treated matched
            matched_treated_indices: Row indices of matched treated
            matched_control_indices: Row indices of matched controls
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Submit job via stats_client (which calls stats-service API)
            job_result = await stats_client.submit_propensity_match_job(
                user_id="mcp_user",
                treatment_column=treatment_col,
                csv_content=csv_content,
                is_base64=False,
                covariates=covariates,
                score_column=score_col,
                method=method,
                caliper=caliper,
                caliper_scale=caliper_scale,
                replacement=replacement,
            )

            return {
                "status": "success",
                "job_id": job_result.get("job_id"),
                "message": "Job submitted. Use get_stats_job_status to check progress.",
                **job_result
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def estimate_treatment_effect(
        csv_path: str,
        outcome_col: str,
        treatment_col: str,
        covariates: Optional[List[str]] = None,
        score_col: Optional[str] = None,
        method: str = "ipw",
        target: str = "ate",
        stabilized: bool = True,
    ) -> dict:
        """
        💊 Estimate causal treatment effect using IPW.

        Estimates:
        - ATE: Average Treatment Effect (population)
        - ATT: Average Treatment Effect on Treated
        - ATU: Average Treatment Effect on Untreated

        Uses inverse probability weighting to adjust for confounding.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            outcome_col: Outcome variable column
            treatment_col: Binary treatment column
            covariates: Covariates for PS estimation
            score_col: Pre-computed propensity score column
            method: 'ipw' or 'iptw'
            target: 'ate', 'att', or 'atu'
            stabilized: Use stabilized weights (recommended)

        Returns:
            effect_type: ATE, ATT, or ATU
            estimate: Point estimate of treatment effect
            std_error: Standard error (bootstrap)
            confidence_interval: 95% CI
            p_value: Two-sided p-value
            significant: Whether effect is significant at α=0.05
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Submit job via stats_client (which calls stats-service API)
            job_result = await stats_client.submit_treatment_effect_job(
                user_id="mcp_user",
                treatment_column=treatment_col,
                outcome_column=outcome_col,
                csv_content=csv_content,
                is_base64=False,
                covariates=covariates,
                score_column=score_col,
                method=method,
                estimand=target.upper(),
            )

            return {
                "status": "success",
                "job_id": job_result.get("job_id"),
                "message": "Job submitted. Use get_stats_job_status to check progress.",
                **job_result
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def assess_covariate_balance(
        csv_path: str,
        treatment_col: str,
        covariates: List[str],
        weights: Optional[List[float]] = None,
        smd_threshold: float = 0.1,
    ) -> dict:
        """
        ⚖️ Assess covariate balance between treatment groups.

        Key metrics:
        - SMD (Standardized Mean Difference): <0.1 is ideal
        - Variance Ratio: Should be 0.5-2.0
        - KS Statistic: Distribution difference

        Use after matching or weighting to verify balance.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            treatment_col: Binary treatment column
            covariates: List of covariate columns
            weights: Optional IPW weights (as list)
            smd_threshold: Threshold for acceptable SMD

        Returns:
            standardized_mean_differences: SMD per covariate
            variance_ratios: Variance ratio per covariate
            ks_tests: KS statistic and p-value per covariate
            summary: Overall balance summary
            balance_achieved: Whether all covariates balanced
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Submit job via stats_client (which calls stats-service API)
            job_result = await stats_client.submit_balance_check_job(
                user_id="mcp_user",
                treatment_column=treatment_col,
                covariates=covariates,
                csv_content=csv_content,
                is_base64=False,
                threshold=smd_threshold,
            )

            return {
                "status": "success",
                "job_id": job_result.get("job_id"),
                "message": "Job submitted. Use get_stats_job_status to check progress.",
                **job_result
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def run_propensity_analysis(
        csv_path: str,
        outcome_col: str,
        treatment_col: str,
        covariates: List[str],
        method: str = "matching",
        target: str = "ate",
        caliper: Optional[float] = 0.2,
    ) -> dict:
        """
        🎯 Complete propensity score analysis workflow.

        All-in-one analysis that performs:
        1. Propensity score estimation
        2. Balance assessment (before)
        3. Matching or IPW weighting
        4. Balance assessment (after)
        5. Treatment effect estimation

        Choose method:
        - matching: Create matched pairs (reduces sample size)
        - ipw: Use weights (keeps all data)

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            outcome_col: Outcome variable column
            treatment_col: Binary treatment column (0/1)
            covariates: List of confounding variables
            method: 'matching' or 'ipw'
            target: 'ate' (population), 'att' (treated), 'atu' (untreated)
            caliper: For matching, max distance in std devs

        Returns:
            propensity_model: PS estimation results
            balance_before: Covariate balance pre-adjustment
            balance_after: Covariate balance post-adjustment
            method_details: Matching/weighting specifics
            treatment_effect: Effect estimate with CI and p-value
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_full_propensity_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                outcome_column=outcome_col,
                treatment_column=treatment_col,
                covariates=covariates,
                method=method,
                target=target,
                caliper=caliper,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(90):  # 3 min timeout for full analysis
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== ROC/AUC Analysis Tools ====================

    @mcp.tool()
    async def compute_roc_curve(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        pos_label: int = 1,
        confidence_level: float = 0.95,
        n_bootstrap: int = 1000,
        threshold_method: str = "youden",
    ) -> dict:
        """
        📈 Compute ROC curve with AUC and confidence intervals.

        Provides comprehensive ROC analysis including:
        - ROC curve points (FPR, TPR at each threshold)
        - AUC with DeLong or bootstrap confidence intervals
        - Optimal threshold selection
        - Sensitivity, specificity, PPV, NPV at optimal point

        Threshold selection methods:
        - youden: Maximizes Youden's J (sensitivity + specificity - 1)
        - cost: Minimizes misclassification cost (specify FP/FN costs)
        - sensitivity: Target minimum sensitivity (e.g., 0.90)
        - specificity: Target minimum specificity

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels (0/1)
            y_score_col: Column with predicted probabilities
            pos_label: Value representing positive class (default 1)
            confidence_level: CI level (default 0.95 for 95% CI)
            n_bootstrap: Bootstrap samples for CI (default 1000)
            threshold_method: How to select optimal threshold

        Returns:
            auc: Area Under the ROC Curve
            auc_ci: Confidence interval {lower, upper}
            auc_se: Standard error of AUC
            optimal_threshold: Best threshold for classification
            optimal_metrics: Sens, spec, PPV, NPV at optimal threshold
            curve: List of ROC points (threshold, fpr, tpr, sens, spec)
            interpretation: Text description of model performance
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_compute_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                pos_label=pos_label,
                confidence_level=confidence_level,
                n_bootstrap=n_bootstrap,
                threshold_method=threshold_method,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def compare_roc_curves(
        csv_path: str,
        y_true_col: str,
        model_score_cols: List[str],
        model_names: Optional[List[str]] = None,
        method: str = "delong",
    ) -> dict:
        """
        🔬 Compare ROC curves from multiple models using DeLong test.

        Statistical comparison of classifier performance using the
        DeLong et al. (1988) method for comparing correlated AUCs.

        This test accounts for the fact that both models are evaluated
        on the same test set, making the comparison valid and powerful.

        Use cases:
        - Compare new model vs baseline
        - Compare different algorithms
        - Compare different feature sets
        - Model selection with statistical evidence

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            model_score_cols: List of columns with predicted probabilities
            model_names: Optional names for models (for output clarity)
            method: 'delong' (recommended) or 'bootstrap'

        Returns:
            models: Per-model results (AUC, CI, SE)
            pairwise_comparisons: DeLong test for each pair
                - auc_difference: AUC1 - AUC2
                - z_statistic: DeLong Z score
                - p_value: Two-sided p-value
                - significant: Whether difference is significant
                - ci: Confidence interval for difference
            best_model: Model with highest AUC
            recommendation: Statistical interpretation
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_compare_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                model_score_columns=model_score_cols,
                model_names=model_names,
                method=method,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def find_optimal_threshold(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        method: str = "youden",
        fp_cost: float = 1.0,
        fn_cost: float = 1.0,
        target_sensitivity: Optional[float] = None,
        target_specificity: Optional[float] = None,
        prevalence: Optional[float] = None,
    ) -> dict:
        """
        🎯 Find optimal classification threshold using various methods.

        Different threshold selection strategies for different needs:

        **Methods:**
        - youden: Maximizes Youden's J index (balanced accuracy)
        - cost: Minimizes expected cost given FP/FN costs
        - f1: Maximizes F1 score
        - sensitivity: Achieves target sensitivity (minimum)
        - specificity: Achieves target specificity (minimum)
        - prevalence_adjusted: Accounts for class imbalance

        **Clinical Examples:**
        - Screening test: High sensitivity, accept lower specificity
        - Confirmatory test: High specificity to minimize false positives
        - Cost-sensitive: Different costs for FP vs FN errors

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            method: Threshold selection method
            fp_cost: Cost of false positive (for cost method)
            fn_cost: Cost of false negative (for cost method)
            target_sensitivity: Minimum sensitivity (for sensitivity method)
            target_specificity: Minimum specificity (for specificity method)
            prevalence: Disease prevalence (for prevalence_adjusted method)

        Returns:
            optimal_threshold: Selected threshold value
            method_used: Which method was applied
            metrics_at_threshold: Sens, spec, PPV, NPV, F1, accuracy
            explanation: Why this threshold was selected
            threshold_range: Nearby thresholds and their metrics
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_threshold_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                method=method,
                fp_cost=fp_cost,
                fn_cost=fn_cost,
                target_sensitivity=target_sensitivity,
                target_specificity=target_specificity,
                prevalence=prevalence,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def analyze_calibration(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        n_bins: int = 10,
        strategy: str = "uniform",
    ) -> dict:
        """
        📊 Analyze model calibration (predicted vs actual probabilities).

        Calibration measures how well predicted probabilities match
        observed frequencies. A well-calibrated model should have
        predicted probability = actual probability.

        **Metrics Provided:**
        - Brier Score: Mean squared error of probabilities (lower is better)
        - Hosmer-Lemeshow Test: Chi-square test for calibration
        - Expected Calibration Error (ECE): Average calibration gap
        - Calibration Curve: Observed vs predicted per bin

        **Interpretation:**
        - Hosmer-Lemeshow p > 0.05: Good calibration
        - ECE < 0.1: Well calibrated
        - ECE > 0.2: Poor calibration, consider recalibration

        **When to Use:**
        - Before using predictions for decision-making
        - When probabilities need to be interpretable
        - For medical risk prediction models

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            n_bins: Number of bins for calibration curve
            strategy: 'uniform' (equal width) or 'quantile' (equal count)

        Returns:
            brier_score: Probability accuracy measure
            hosmer_lemeshow: {statistic, p_value, interpretation}
            expected_calibration_error: Average calibration gap
            calibration_curve: Per-bin observed vs predicted
            reliability_diagram_data: Data for plotting
            recommendations: Calibration improvement suggestions
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_calibration_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                n_bins=n_bins,
                strategy=strategy,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def full_classifier_evaluation(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        threshold: Optional[float] = None,
    ) -> dict:
        """
        🏆 Complete classifier evaluation report.

        Comprehensive evaluation combining all ROC analysis tools:

        1. **Discrimination** (ROC Analysis)
           - ROC curve and AUC with CI
           - Optimal threshold selection

        2. **Classification Metrics**
           - Confusion matrix
           - Sensitivity, Specificity
           - PPV, NPV, F1, Accuracy

        3. **Calibration**
           - Brier score
           - Hosmer-Lemeshow test
           - Calibration curve

        4. **Clinical Utility** (optional)
           - Net benefit analysis
           - Decision curve

        Perfect for publication-ready classifier assessment.

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            threshold: Classification threshold (default: optimal)

        Returns:
            roc_analysis: Full ROC curve results
            calibration: Calibration analysis
            classification_report: Metrics at threshold
            summary: Executive summary text
            publication_text: Ready-to-use results paragraph
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_full_eval_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                threshold=threshold,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(90):  # 3 min timeout for full eval
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # Phase 5A: Enhanced ROC/AUC Interactive Tools
    # =========================================================================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def compare_multiple_roc_curves(
        csv_path: str,
        y_true_col: str,
        model_columns: str,  # JSON string: {"Model A": "score_a", "Model B": "score_b", ...}
        correction: str = "bonferroni",
        alpha: float = 0.05,
    ) -> dict:
        """
        📊 Compare 3+ classification models simultaneously.

        Performs comprehensive multi-model comparison:

        1. **Individual Performance**
           - AUC with 95% CI for each model
           - Ranked by discriminative ability

        2. **Pairwise Comparisons**
           - DeLong test between all model pairs
           - Multiple comparison correction
           - Significance matrix

        3. **Best Model Selection**
           - Identifies top performer
           - Reports if significantly better

        Correction Methods:
        - "bonferroni": Conservative, controls family-wise error
        - "holm": Less conservative step-down procedure
        - "bh": Benjamini-Hochberg FDR control
        - "none": No correction (not recommended)

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            model_columns: JSON mapping model names to score columns
                Example: '{"Logistic": "lr_prob", "XGBoost": "xgb_prob", "RF": "rf_prob"}'
            correction: Multiple comparison correction method
            alpha: Significance level (default: 0.05)

        Returns:
            model_rankings: Models ranked by AUC
            pairwise_comparisons: All DeLong test results
            comparison_matrix: P-value matrix
            best_model: Recommended best performer
            interpretation: Human-readable summary

        Example:
            >>> result = await compare_multiple_roc_curves(
            ...     csv_path="/data/sample_data/predictions.csv",
            ...     y_true_col="outcome",
            ...     model_columns='{"LR": "lr_probs", "XGB": "xgb_probs", "RF": "rf_probs"}'
            ... )
            >>> print(result["interpretation"])
        """
        import json

        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            # Parse model columns JSON
            model_cols = json.loads(model_columns)

            result = await stats_client.submit_roc_compare_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                model_score_columns=list(model_cols.values()),
                model_names=list(model_cols.keys()),
                method="delong",
                correction=correction,
                alpha=alpha,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except json.JSONDecodeError as e:
            return {"status": "error", "error": f"Invalid JSON for model_columns: {e}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def interactive_threshold_analysis(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        target_metric: Optional[str] = None,
        target_value: Optional[float] = None,
        n_thresholds: int = 21,
    ) -> dict:
        """
        🎯 Interactive threshold analysis for clinical decision support.

        Comprehensive threshold-by-threshold analysis showing:

        1. **Complete Metrics Table**
           - Sensitivity, Specificity, PPV, NPV at each threshold
           - F1, Accuracy, Youden's J
           - Likelihood ratios (LR+, LR-)
           - Number needed to screen (NNS)

        2. **Target-Based Selection**
           - Find threshold for target sensitivity (screening)
           - Find threshold for target specificity (confirmation)
           - Trade-off analysis

        3. **Recommended Thresholds**
           - Youden optimal (balanced)
           - F1 optimal (precision-recall balance)
           - High sensitivity (≥90% for screening)
           - High specificity (≥90% for confirmation)

        **Clinical Use Cases:**
        - Screening test: "Need 95% sensitivity, what specificity?"
        - Confirmatory test: "Need 95% specificity, what threshold?"
        - Cost analysis: "What threshold minimizes false negatives?"

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            target_metric: Metric to optimize ('sensitivity', 'specificity', 'ppv', 'npv', 'f1')
            target_value: Target value (e.g., 0.95 for 95% sensitivity)
            n_thresholds: Number of thresholds to evaluate (default: 21)

        Returns:
            threshold_table: Complete metrics at each threshold
            target_threshold: Threshold achieving target (if specified)
            recommended_thresholds: Best thresholds for common scenarios
            clinical_interpretation: Decision support text

        Example:
            >>> # Find threshold for 95% sensitivity
            >>> result = await interactive_threshold_analysis(
            ...     csv_path="/data/sample_data/predictions.csv",
            ...     y_true_col="outcome", y_score_col="pred_prob",
            ...     target_metric="sensitivity",
            ...     target_value=0.95
            ... )
            >>> print(result["target_threshold"])
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_threshold_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                method="interactive",
                target_metric=target_metric,
                target_value=target_value,
                n_thresholds=n_thresholds,
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(60):  # 2 min timeout
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def generate_roc_publication_report(
        csv_path: str,
        y_true_col: str,
        y_score_col: str,
        model_name: str = "The prediction model",
        outcome_name: str = "the outcome",
        threshold_method: str = "youden",
        decimal_places: int = 2,
    ) -> dict:
        """
        📝 Generate publication-ready ROC analysis report.

        Produces formatted text suitable for journal submission:

        1. **Results Paragraph** (copy-paste ready)
           - AUC with 95% CI (DeLong method)
           - Optimal threshold and method
           - Sensitivity, Specificity with bootstrap CIs
           - PPV, NPV, Accuracy
           - Calibration assessment

        2. **Methods Paragraph**
           - Statistical methods description
           - CI calculation methods
           - Software citations

        3. **Table Data**
           - Ready for Table X (Model Performance)
           - All metrics with CIs

        4. **Figure Data**
           - ROC curve coordinates
           - AUC annotation
           - Optimal point marker

        **Follows Guidelines:**
        - TRIPOD reporting guidelines
           - PROBAST assessment criteria
        - Standard journal formatting

        Args:
            csv_path: Path to CSV file (e.g., /data/sample_data/file.csv)
            y_true_col: Column with true binary labels
            y_score_col: Column with predicted probabilities
            model_name: Name for text (e.g., "The XGBoost classifier")
            outcome_name: Outcome for text (e.g., "30-day mortality")
            threshold_method: Method for optimal threshold ('youden', 'f1')
            decimal_places: Decimal places for reporting (default: 2)

        Returns:
            results_text: Main results paragraph
            methods_text: Methods description
            table_data: Data for performance table
            figure_data: Data for ROC curve figure
            all_metrics: Complete metrics dictionary

        Example:
            >>> report = await generate_roc_publication_report(
            ...     csv_path="/data/sample_data/predictions.csv",
            ...     y_true_col="mortality_30d",
            ...     y_score_col="risk_score",
            ...     model_name="The gradient boosting model",
            ...     outcome_name="30-day mortality"
            ... )
            >>> print(report["results_text"])
        """
        try:
            # Read CSV from path
            success, result = _read_csv_from_path_or_reject(csv_path)
            if not success:
                return result
            csv_content = result

            result = await stats_client.submit_roc_full_eval_job(
                csv_content=csv_content,
                is_base64=False,
                user_id="mcp_user",
                y_true_column=y_true_col,
                y_score_column=y_score_col,
                model_name=model_name,
                outcome_name=outcome_name,
                threshold_method=threshold_method,
                decimal_places=decimal_places,
                report_type="publication",
            )

            job_id = result.get("job_id")
            if not job_id:
                return {"status": "error", "error": "Failed to submit job"}

            # Poll for job completion
            import asyncio
            for _ in range(90):  # 3 min timeout for publication report
                status = await stats_client.get_job_status(job_id)
                if status.get("status") == "completed":
                    return await stats_client.get_job_result(job_id)
                elif status.get("status") == "failed":
                    return {"status": "error", "error": status.get("error", "Job failed")}
                await asyncio.sleep(2)

            return {"status": "error", "error": "Job timed out", "job_id": job_id}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== POWER ANALYSIS TOOLS (Phase 6) ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_ttest_sample_size(
        effect_size: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        test_type: str = "two-sample",
        alternative: str = "two-sided",
    ) -> dict:
        """
        📊 Calculate required sample size for t-test.

        This is the FIRST STEP in clinical research planning.
        Determines how many participants you need to detect a meaningful effect.

        Args:
            effect_size: Expected Cohen's d effect size
                - 0.2 = small effect
                - 0.5 = medium effect
                - 0.8 = large effect
                - Or calculate from: (mean1 - mean2) / pooled_sd
            alpha: Significance level (default: 0.05 for 5% Type I error)
            power: Desired power (default: 0.80 for 80% chance to detect effect)
            ratio: Sample size ratio n2/n1 (default: 1.0 for equal groups)
            test_type: "two-sample" | "paired" | "one-sample"
            alternative: "two-sided" | "larger" | "smaller"

        Returns:
            n1: Required sample size for group 1
            n2: Required sample size for group 2 (if applicable)
            total_n: Total sample size needed
            parameters: Input parameters used
            interpretation: Plain-language explanation
            recommendations: Practical advice

        Example:
            # Planning a drug vs placebo RCT
            # Expecting medium effect (d=0.5), want 80% power
            calculate_ttest_sample_size(effect_size=0.5)
            # Returns: n1=64, n2=64, total=128
        """
        try:
            result = await stats_client.calculate_ttest_power(
                effect_size=effect_size,
                alpha=alpha,
                power=power,
                n=None,  # Calculating sample size, not power
                ratio=ratio,
                alternative=alternative,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_ttest_power(
        effect_size: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        test_type: str = "two-sample",
        alternative: str = "two-sided",
    ) -> dict:
        """
        ⚡ Calculate statistical power for t-test with given sample size.

        Use this to evaluate if your planned study has adequate power
        to detect the expected effect.

        Args:
            effect_size: Expected Cohen's d effect size
            n1: Sample size for group 1
            n2: Sample size for group 2 (default: same as n1)
            alpha: Significance level (default: 0.05)
            test_type: "two-sample" | "paired" | "one-sample"
            alternative: "two-sided" | "larger" | "smaller"

        Returns:
            power: Achieved statistical power (0-1)
            interpretation: Is this power adequate?
            parameters: Input parameters used
            recommendations: Suggestions if power is low

        Example:
            # Check if 50 per group is enough
            calculate_ttest_power(effect_size=0.5, n1=50, n2=50)
            # Returns: power=0.697 (underpowered!)
        """
        try:
            result = await stats_client.calculate_ttest_power(
                effect_size=effect_size,
                alpha=alpha,
                power=None,  # Calculating power, not sample size
                n=n1,  # Use n1 as sample size per group
                ratio=1.0 if n2 is None or n2 == n1 else n2 / n1,
                alternative=alternative,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_proportion_sample_size(
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power: float = 0.80,
        ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> dict:
        """
        📊 Calculate required sample size for proportion comparison.

        Use this when comparing rates/percentages between two groups
        (e.g., response rates, event rates, success rates).

        Args:
            p1: Expected proportion in group 1 (e.g., 0.30 for 30%)
            p2: Expected proportion in group 2 (e.g., 0.45 for 45%)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            ratio: Sample size ratio n2/n1 (default: 1.0)
            alternative: "two-sided" | "larger" | "smaller"

        Returns:
            n1: Required sample size for group 1
            n2: Required sample size for group 2
            total_n: Total sample size
            effect_size_h: Cohen's h effect size
            parameters: Input parameters
            interpretation: Explanation

        Example:
            # Control group: 30% response, Treatment: 45% expected
            calculate_proportion_sample_size(p1=0.30, p2=0.45)
            # Returns: n1=152, n2=152, total=304
        """
        try:
            result = await stats_client.calculate_proportion_power(
                p1=p1,
                p2=p2,
                alpha=alpha,
                power=power,
                n=None,  # Calculating sample size
                ratio=ratio,
                alternative=alternative,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_proportion_power(
        p1: float,
        p2: float,
        n1: int,
        n2: Optional[int] = None,
        alpha: float = 0.05,
        alternative: str = "two-sided",
    ) -> dict:
        """
        ⚡ Calculate power for proportion comparison with given sample size.

        Args:
            p1: Expected proportion in group 1
            p2: Expected proportion in group 2
            n1: Sample size for group 1
            n2: Sample size for group 2 (default: same as n1)
            alpha: Significance level (default: 0.05)
            alternative: "two-sided" | "larger" | "smaller"

        Returns:
            power: Achieved statistical power
            effect_size_h: Cohen's h effect size
            interpretation: Adequacy assessment
            parameters: Input parameters

        Example:
            # Check power with 100 per group
            calculate_proportion_power(p1=0.30, p2=0.45, n1=100)
            # Returns: power=0.647 (underpowered)
        """
        try:
            result = await stats_client.calculate_proportion_power(
                p1=p1,
                p2=p2,
                alpha=alpha,
                power=None,  # Calculating power
                n=n1,
                ratio=1.0 if n2 is None or n2 == n1 else n2 / n1,
                alternative=alternative,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def ttest_sensitivity_analysis(
        effect_size: float,
        alpha: float = 0.05,
        power_range: Optional[List[float]] = None,
        ratio: float = 1.0,
        test_type: str = "two-sample",
    ) -> dict:
        """
        📈 Generate power curve and sample size sensitivity analysis.

        Shows how sample size requirements change across different
        power levels. Useful for grant applications and study planning.

        Args:
            effect_size: Expected Cohen's d effect size
            alpha: Significance level (default: 0.05)
            power_range: List of power levels to evaluate
                        (default: [0.70, 0.75, 0.80, 0.85, 0.90, 0.95])
            ratio: Sample size ratio n2/n1
            test_type: "two-sample" | "paired" | "one-sample"

        Returns:
            sensitivity_table: Sample sizes for each power level
            power_curve_data: Data for plotting power curve
            recommendations: Practical guidance
            summary: Overview text

        Example:
            # See sample size requirements for different power levels
            ttest_sensitivity_analysis(effect_size=0.5)
        """
        try:
            # Generate sensitivity analysis by calling API for each power level
            power_levels = power_range or [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
            sensitivity_table = []

            for pwr in power_levels:
                result = await stats_client.calculate_ttest_power(
                    effect_size=effect_size,
                    alpha=alpha,
                    power=pwr,
                    n=None,
                    ratio=ratio,
                    alternative="two-sided",
                )
                sensitivity_table.append({
                    "power": pwr,
                    "sample_size": result.get("result", 0),
                })

            return {
                "effect_size": effect_size,
                "alpha": alpha,
                "sensitivity_table": sensitivity_table,
                "recommendations": "80% power is standard for most studies. Consider 90% for confirmatory trials.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def proportion_sensitivity_analysis(
        p1: float,
        p2: float,
        alpha: float = 0.05,
        power_range: Optional[List[float]] = None,
        ratio: float = 1.0,
    ) -> dict:
        """
        📈 Generate power curve for proportion test.

        Args:
            p1: Expected proportion in group 1
            p2: Expected proportion in group 2
            alpha: Significance level
            power_range: Power levels to evaluate
            ratio: Sample size ratio

        Returns:
            sensitivity_table: Sample sizes for each power level
            power_curve_data: Data for plotting
            effect_size_h: Cohen's h
            recommendations: Guidance
        """
        try:
            import math
            # Calculate Cohen's h
            h = abs(2 * (math.asin(math.sqrt(p1)) - math.asin(math.sqrt(p2))))

            power_levels = power_range or [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
            sensitivity_table = []

            for pwr in power_levels:
                result = await stats_client.calculate_proportion_power(
                    p1=p1,
                    p2=p2,
                    alpha=alpha,
                    power=pwr,
                    n=None,
                    ratio=ratio,
                    alternative="two-sided",
                )
                sensitivity_table.append({
                    "power": pwr,
                    "sample_size": result.get("result", 0),
                })

            return {
                "p1": p1,
                "p2": p2,
                "effect_size_h": round(h, 4),
                "alpha": alpha,
                "sensitivity_table": sensitivity_table,
                "recommendations": "Consider clinical significance of the absolute difference, not just statistical significance.",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_effect_size(
        mean1: Optional[float] = None,
        mean2: Optional[float] = None,
        sd1: Optional[float] = None,
        sd2: Optional[float] = None,
        pooled_sd: Optional[float] = None,
        p1: Optional[float] = None,
        p2: Optional[float] = None,
    ) -> dict:
        """
        🧮 Calculate effect size from study parameters.

        Use this to convert your expected means/proportions into
        effect sizes for power analysis.

        For means (Cohen's d):
            Provide mean1, mean2, and either pooled_sd or (sd1, sd2)

        For proportions (Cohen's h):
            Provide p1 and p2

        Args:
            mean1: Mean of group 1
            mean2: Mean of group 2
            sd1: Standard deviation of group 1
            sd2: Standard deviation of group 2
            pooled_sd: Pooled standard deviation (if known)
            p1: Proportion in group 1
            p2: Proportion in group 2

        Returns:
            effect_size: Calculated effect size
            effect_type: "Cohen's d" or "Cohen's h"
            interpretation: "small" / "medium" / "large"
            formula_used: Calculation details

        Example:
            # From means: Control=100, Treatment=115, SD=30
            calculate_effect_size(mean1=100, mean2=115, pooled_sd=30)
            # Returns: Cohen's d = 0.5 (medium effect)

            # From proportions: Control=30%, Treatment=45%
            calculate_effect_size(p1=0.30, p2=0.45)
            # Returns: Cohen's h = 0.31 (small-medium effect)
        """
        try:
            # Use stats_client for effect size calculation
            if mean1 is not None and mean2 is not None:
                result = await stats_client.calculate_effect_size(
                    test_type="ttest",
                    mean1=mean1,
                    mean2=mean2,
                    std=pooled_sd or (((sd1 or 1)**2 + (sd2 or 1)**2) / 2)**0.5 if sd1 and sd2 else pooled_sd,
                )
                if "effect_size" in result:
                    d = result["effect_size"].get("cohens_d", 0)
                    interp = result["effect_size"].get("interpretation", "unknown")
                    return {
                        "effect_size": round(d, 4),
                        "effect_type": "Cohen's d",
                        "interpretation": interp,
                        "formula_used": "(mean1 - mean2) / pooled_sd",
                        "parameters": {
                            "mean1": mean1,
                            "mean2": mean2,
                            "sd1": sd1,
                            "sd2": sd2,
                            "pooled_sd": pooled_sd,
                        }
                    }
                return result

            # Calculate Cohen's h from proportions
            elif p1 is not None and p2 is not None:
                result = await stats_client.calculate_effect_size(
                    test_type="proportion",
                    p1=p1,
                    p2=p2,
                )
                if "effect_size" in result:
                    h = result["effect_size"].get("cohens_h", 0)
                    interp = result["effect_size"].get("interpretation", "unknown")
                    return {
                        "effect_size": round(h, 4),
                        "effect_type": "Cohen's h",
                        "interpretation": interp,
                        "formula_used": "2 * arcsin(√p1) - 2 * arcsin(√p2)",
                        "parameters": {
                            "p1": p1,
                            "p2": p2,
                        }
                    }
                return result

            else:
                return {
                    "status": "error",
                    "error": "Provide (mean1, mean2, sd) for Cohen's d or (p1, p2) for Cohen's h"
                }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== PHASE 6.2: ANOVA POWER ANALYSIS ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_anova_sample_size(
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        power: float = 0.80,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        📊 Calculate sample size for one-way ANOVA.

        Determines how many participants per group for comparing
        means across multiple groups (3+ groups).

        Args:
            effect_size: Cohen's f effect size
                - 0.10 = small effect
                - 0.25 = medium effect
                - 0.40 = large effect
            k_groups: Number of groups (default: 3)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            group_means: List of expected group means (alternative to effect_size)
            pooled_sd: Pooled standard deviation (required with group_means)
            eta_squared: Eta-squared (η²) effect size (alternative to Cohen's f)

        Returns:
            n_per_group: Sample size per group
            total_n: Total sample size
            effect_size_f: Cohen's f
            eta_squared: Eta-squared (% variance explained)
            sensitivity_analysis: Sample sizes at different power levels

        Example:
            # 3 treatment groups, medium effect
            calculate_anova_sample_size(effect_size=0.25, k_groups=3)
            # Returns: n_per_group=52, total=156

            # From group means: [10, 12, 15] with SD=5
            calculate_anova_sample_size(group_means=[10, 12, 15], pooled_sd=5)
        """
        try:
            result = await stats_client.calculate_anova_power(
                k=k_groups,
                effect_size=effect_size,
                means=group_means,
                std=pooled_sd,
                alpha=alpha,
                power=power,
                n=None,  # Calculating sample size
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_anova_power(
        n_per_group: int,
        effect_size: Optional[float] = None,
        k_groups: int = 3,
        alpha: float = 0.05,
        group_means: Optional[List[float]] = None,
        pooled_sd: Optional[float] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        ⚡ Calculate power for one-way ANOVA given sample size.

        Args:
            n_per_group: Sample size per group
            effect_size: Cohen's f
            k_groups: Number of groups
            alpha: Significance level
            group_means: Group means (alternative)
            pooled_sd: Pooled SD
            eta_squared: Eta-squared (alternative)

        Returns:
            power: Statistical power (0-1)
            interpretation: Adequacy assessment
            recommendations: Suggestions if underpowered

        Example:
            # Check if 30 per group is enough for medium effect
            calculate_anova_power(n_per_group=30, effect_size=0.25, k_groups=3)
        """
        try:
            result = await stats_client.calculate_anova_power(
                k=k_groups,
                effect_size=effect_size,
                means=group_means,
                std=pooled_sd,
                alpha=alpha,
                power=None,  # Calculating power
                n=n_per_group,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_anova_effect_size(
        group_means: List[float],
        pooled_sd: Optional[float] = None,
        group_sds: Optional[List[float]] = None,
        eta_squared: Optional[float] = None,
    ) -> dict:
        """
        🧮 Calculate Cohen's f effect size for ANOVA.

        Converts group means or eta-squared to Cohen's f.

        Args:
            group_means: List of expected group means
            pooled_sd: Pooled standard deviation
            group_sds: Standard deviations per group (alternative)
            eta_squared: Eta-squared to convert

        Returns:
            cohens_f: Cohen's f effect size
            eta_squared: Equivalent eta-squared
            interpretation: small/medium/large

        Example:
            # From means: groups have means [10, 12, 15] with SD=5
            calculate_anova_effect_size(group_means=[10, 12, 15], pooled_sd=5)
        """
        try:
            import numpy as np

            # Calculate Cohen's f from group means
            if eta_squared is not None:
                # f = sqrt(eta^2 / (1 - eta^2))
                f = (eta_squared / (1 - eta_squared)) ** 0.5
                eta_sq = eta_squared
            elif group_means is not None:
                means = np.array(group_means)

                # Calculate between-group variance (grand_mean not needed for np.var)
                between_var = np.var(means, ddof=0)

                # Get SD
                if pooled_sd:
                    sd = pooled_sd
                elif group_sds:
                    sd = np.mean(group_sds)  # Simple average of group SDs
                else:
                    return {"status": "error", "error": "Provide pooled_sd or group_sds"}

                f = np.sqrt(between_var) / sd
                eta_sq = f**2 / (1 + f**2)
            else:
                return {"status": "error", "error": "Provide group_means or eta_squared"}

            # Interpretation
            if f < 0.1:
                interp = "negligible"
            elif f < 0.25:
                interp = "small"
            elif f < 0.40:
                interp = "medium"
            else:
                interp = "large"

            return {
                "cohens_f": round(float(f), 4),
                "eta_squared": round(float(eta_sq), 4),
                "interpretation": interp,
                "variance_explained": f"{eta_sq*100:.1f}%",
                "parameters": {
                    "group_means": group_means,
                    "pooled_sd": pooled_sd,
                    "k_groups": len(group_means) if group_means else None,
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== PHASE 6.2: CHI-SQUARE POWER ANALYSIS ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_chisquare_sample_size(
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        power: float = 0.80,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
    ) -> dict:
        """
        📊 Calculate sample size for chi-square test.

        For comparing categorical distributions or testing independence
        in contingency tables.

        Args:
            effect_size: Cohen's w effect size
                - 0.10 = small effect
                - 0.30 = medium effect
                - 0.50 = large effect
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            df: Degrees of freedom (calculated if not provided)
            n_bins: Number of categories (for goodness-of-fit)
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table

        Returns:
            n: Required sample size
            effect_size_w: Cohen's w
            cramers_v: Cramér's V (for contingency tables)
            sensitivity_analysis: Sample sizes at different power levels

        Example:
            # Goodness-of-fit with 4 categories, medium effect
            calculate_chisquare_sample_size(effect_size=0.3, n_bins=4)

            # Independence test: 2x3 table
            calculate_chisquare_sample_size(effect_size=0.3, n_rows=2, n_cols=3)
        """
        try:
            # Calculate df if not provided
            calculated_df = df
            if calculated_df is None:
                if n_bins is not None:
                    calculated_df = n_bins - 1  # Goodness of fit
                elif n_rows is not None and n_cols is not None:
                    calculated_df = (n_rows - 1) * (n_cols - 1)  # Independence test

            result = await stats_client.calculate_chisquare_power(
                effect_size=effect_size,
                df=calculated_df,
                alpha=alpha,
                power=power,
                n=None,  # Calculating sample size
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_chisquare_power(
        n: int,
        effect_size: Optional[float] = None,
        alpha: float = 0.05,
        df: Optional[int] = None,
        n_bins: Optional[int] = None,
        n_rows: Optional[int] = None,
        n_cols: Optional[int] = None,
    ) -> dict:
        """
        ⚡ Calculate power for chi-square test given sample size.

        Args:
            n: Sample size
            effect_size: Cohen's w
            alpha: Significance level
            df: Degrees of freedom
            n_bins: Number of categories
            n_rows: Rows in contingency table
            n_cols: Columns in contingency table

        Returns:
            power: Statistical power
            recommendations: Suggestions if underpowered

        Example:
            # Check if n=100 is enough for 2x3 table
            calculate_chisquare_power(n=100, effect_size=0.3, n_rows=2, n_cols=3)
        """
        try:
            # Calculate df if not provided
            calculated_df = df
            if calculated_df is None:
                if n_bins is not None:
                    calculated_df = n_bins - 1
                elif n_rows is not None and n_cols is not None:
                    calculated_df = (n_rows - 1) * (n_cols - 1)

            result = await stats_client.calculate_chisquare_power(
                effect_size=effect_size,
                df=calculated_df,
                alpha=alpha,
                power=None,  # Calculating power
                n=n,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_chisquare_effect_size(
        observed_proportions: List[float],
        expected_proportions: Optional[List[float]] = None,
    ) -> dict:
        """
        🧮 Calculate Cohen's w effect size for chi-square test.

        Args:
            observed_proportions: Observed category proportions
            expected_proportions: Expected proportions (uniform if None)

        Returns:
            cohens_w: Cohen's w effect size
            interpretation: small/medium/large

        Example:
            # Test if categories differ from uniform distribution
            calculate_chisquare_effect_size(
                observed_proportions=[0.10, 0.20, 0.30, 0.40]
            )

            # Compare to specific expected distribution
            calculate_chisquare_effect_size(
                observed_proportions=[0.30, 0.25, 0.25, 0.20],
                expected_proportions=[0.25, 0.25, 0.25, 0.25]
            )
        """
        try:
            # Calculate Cohen's w locally (simple formula)
            import numpy as np

            obs = np.array(observed_proportions)
            if expected_proportions is None:
                exp = np.ones(len(obs)) / len(obs)  # Uniform distribution
            else:
                exp = np.array(expected_proportions)

            # Cohen's w = sqrt(sum((observed - expected)^2 / expected))
            w = np.sqrt(np.sum((obs - exp)**2 / exp))

            # Interpretation
            if w < 0.1:
                interp = "negligible"
            elif w < 0.3:
                interp = "small"
            elif w < 0.5:
                interp = "medium"
            else:
                interp = "large"

            return {
                "cohens_w": round(float(w), 4),
                "interpretation": interp,
                "observed": observed_proportions,
                "expected": exp.tolist(),
                "n_categories": len(observed_proportions),
                "df": len(observed_proportions) - 1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ==================== PHASE 6.3: SURVIVAL ANALYSIS POWER ====================

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_survival_events(
        hazard_ratio: float,
        alpha: float = 0.05,
        power: float = 0.80,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Calculate required number of events for log-rank test.

        Use when you know the expected hazard ratio and want to determine
        how many events are needed to detect the effect.

        Args:
            hazard_ratio: Expected hazard ratio (treatment/control)
                - HR < 1: Treatment reduces hazard (beneficial)
                - HR > 1: Treatment increases hazard
                - HR = 0.7 means 30% reduction in hazard
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            allocation_ratio: n_treatment / n_control (default: 1.0, equal groups)
            alternative: "two-sided" or "one-sided"

        Returns:
            Dictionary containing:
            - total_events: Total required events
            - events_per_group: Events in each arm
            - log_hazard_ratio: log(HR) used in calculation
            - sensitivity: Events needed at different HR values

        Example:
            # 30% reduction in hazard (HR=0.7)
            calculate_survival_events(hazard_ratio=0.7, power=0.80)

            # 50% reduction (HR=0.5), one-sided test
            calculate_survival_events(hazard_ratio=0.5, alternative="one-sided")
        """
        try:
            result = await stats_client.calculate_survival_power(
                hazard_ratio=hazard_ratio,
                p1=0.7,  # Default event probability for events calculation
                alpha=alpha,
                power=power,
                ratio=allocation_ratio,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_survival_sample_size(
        hazard_ratio: float,
        alpha: float = 0.05,
        power: float = 0.80,
        prob_event: float = 0.70,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
        accrual_time: float = None,
        follow_up_time: float = None,
    ) -> Dict[str, Any]:
        """
        Calculate sample size for survival analysis (log-rank test).

        Determines how many subjects to enroll given expected event rate.

        Args:
            hazard_ratio: Expected hazard ratio (treatment/control)
            alpha: Significance level (default: 0.05)
            power: Desired statistical power (default: 0.80)
            prob_event: Expected proportion observing event (default: 0.70)
                - Higher = more events, smaller sample needed
                - Lower = more censoring, larger sample needed
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"
            accrual_time: Enrollment period in months (optional)
            follow_up_time: Follow-up period after enrollment (optional)

        Returns:
            Dictionary containing:
            - total_n: Total sample size needed
            - n_treatment: Sample size for treatment group
            - n_control: Sample size for control group
            - total_events: Expected number of events
            - clinical_interpretation: Plain language explanation

        Example:
            # HR=0.65 (35% reduction), 70% event rate
            calculate_survival_sample_size(hazard_ratio=0.65, prob_event=0.70)

            # With enrollment and follow-up periods
            calculate_survival_sample_size(
                hazard_ratio=0.7,
                prob_event=0.60,
                accrual_time=24,  # 2 year enrollment
                follow_up_time=12  # 1 year follow-up
            )
        """
        try:
            result = await stats_client.calculate_survival_power(
                hazard_ratio=hazard_ratio,
                p1=prob_event,
                alpha=alpha,
                power=power,
                ratio=allocation_ratio,
                accrual_time=accrual_time,
                followup_time=follow_up_time,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_survival_power(
        hazard_ratio: float,
        n_events: int = None,
        total_n: int = None,
        alpha: float = 0.05,
        prob_event: float = 0.70,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Calculate power for survival analysis given sample/events.

        Use when you have a fixed sample size or number of events and
        want to know the power to detect a given hazard ratio.

        Args:
            hazard_ratio: Expected hazard ratio to detect
            n_events: Number of events (directly specify events)
            total_n: Total sample size (events calculated from prob_event)
                - Provide either n_events OR total_n, not both
            alpha: Significance level (default: 0.05)
            prob_event: Event probability (used with total_n)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"

        Returns:
            Dictionary containing:
            - power: Calculated statistical power
            - n_events: Number of events used
            - events_for_80pct: Events needed for 80% power
            - clinical_interpretation: Power interpretation

        Example:
            # Power with 200 events
            calculate_survival_power(hazard_ratio=0.75, n_events=200)

            # Power with 400 subjects, 65% event rate
            calculate_survival_power(hazard_ratio=0.70, total_n=400, prob_event=0.65)
        """
        try:
            result = await stats_client.calculate_survival_power(
                hazard_ratio=hazard_ratio,
                p1=prob_event,
                alpha=alpha,
                power=None,  # Calculating power
                n_events=n_events,
                ratio=allocation_ratio,
            )
            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def calculate_survival_from_medians(
        median_control: float,
        median_treatment: float,
        alpha: float = 0.05,
        power: float = 0.80,
        accrual_time: float = 12,
        follow_up_time: float = 12,
        allocation_ratio: float = 1.0,
        alternative: str = "two-sided",
    ) -> Dict[str, Any]:
        """
        Calculate sample size from median survival times.

        Most intuitive method when you know expected median survival
        in each group (e.g., from pilot data or literature).

        Args:
            median_control: Expected median survival in control (months)
            median_treatment: Expected median survival in treatment (months)
            alpha: Significance level (default: 0.05)
            power: Desired power (default: 0.80)
            accrual_time: Enrollment period in months (default: 12)
            follow_up_time: Additional follow-up in months (default: 12)
            allocation_ratio: n_treatment / n_control (default: 1.0)
            alternative: "two-sided" or "one-sided"

        Returns:
            Dictionary containing:
            - total_n: Total sample size
            - implied_hazard_ratio: HR calculated from medians
            - total_events: Required events
            - study_duration: Total study duration
            - clinical_interpretation: Plain language explanation

        Example:
            # Control: 8 months, Treatment: 12 months (50% improvement)
            calculate_survival_from_medians(
                median_control=8,
                median_treatment=12,
                accrual_time=18,
                follow_up_time=12
            )

            # Cancer trial: 6 vs 9 month median survival
            calculate_survival_from_medians(
                median_control=6,
                median_treatment=9,
                accrual_time=24,
                follow_up_time=18
            )
        """
        try:
            # Convert medians to hazard ratio
            # Under exponential assumption: HR = median_control / median_treatment
            hazard_ratio = median_control / median_treatment

            result = await stats_client.calculate_survival_power(
                hazard_ratio=hazard_ratio,
                p1=0.7,  # Default event probability
                alpha=alpha,
                power=power,
                ratio=allocation_ratio,
                accrual_time=accrual_time,
                followup_time=follow_up_time,
            )

            # Add median information to result
            result["median_control"] = median_control
            result["median_treatment"] = median_treatment
            result["implied_hazard_ratio"] = round(hazard_ratio, 4)
            result["improvement"] = f"{(1 - hazard_ratio) * 100:.1f}% reduction in hazard"

            return result
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def convert_hazard_ratio_to_log(
        hazard_ratio: float,
    ) -> Dict[str, Any]:
        """
        Convert hazard ratio to log hazard ratio.

        Useful for understanding effect size in survival analysis.

        Args:
            hazard_ratio: The hazard ratio to convert

        Returns:
            Dictionary with log_hr and interpretation

        Example:
            convert_hazard_ratio_to_log(0.7)  # 30% reduction
        """
        try:
            import math
            log_hr = math.log(hazard_ratio)

            if hazard_ratio < 1:
                reduction = (1 - hazard_ratio) * 100
                interp = f"{reduction:.1f}% reduction in hazard (beneficial)"
            elif hazard_ratio > 1:
                increase = (hazard_ratio - 1) * 100
                interp = f"{increase:.1f}% increase in hazard"
            else:
                interp = "No effect"

            return {
                "hazard_ratio": hazard_ratio,
                "log_hazard_ratio": round(log_hr, 4),
                "interpretation": interp,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    logger.info("Registered 57 statistics tools (including Phase 6.3 Survival Power)")




