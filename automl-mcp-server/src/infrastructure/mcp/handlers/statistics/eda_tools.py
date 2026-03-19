"""
EDA (Exploratory Data Analysis) Tools

Provides MCP tools for:
- Auto-analyze (intelligent automatic analysis)
- EDA reports using ydata-profiling
- Quick statistics
- Advanced analysis (correlation, missing values, VIF, group comparisons)
"""

import logging
import time
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_eda_tools(mcp: FastMCP, stats_client) -> None:
    """Register EDA-related MCP tools"""

    # ==================== AUTO-ANALYZE (Smart Analysis) ====================

    @mcp.tool()
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
        """
        return await stats_client.submit_auto_analyze_job(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            target_column=target_column,
        )

    @mcp.tool()
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
            result: Full analysis result
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

    @mcp.tool()
    async def get_analysis_capabilities() -> dict:
        """
        📋 Get capabilities of the auto-analyze engine.

        Returns detailed information about what the auto-analyze
        engine can do, including all tests and metrics available.
        """
        return await stats_client.get_auto_analyze_capabilities()

    # ==================== EDA (ydata-profiling) ====================

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

        Generates a comprehensive data profiling report using ydata-profiling.
        The job runs asynchronously - use get_stats_job_status() to check progress.

        Args:
            dataset_id: ID of the dataset to analyze
            user_id: User ID for isolation
            session_id: Optional session ID
            title: Report title
            minimal: Use minimal mode for faster processing (default: True)

        Returns:
            job_id: Job identifier for tracking
            status: "pending"
        """
        return await stats_client.submit_eda_job(
            dataset_id=dataset_id,
            user_id=user_id,
            session_id=session_id,
            title=title,
            minimal=minimal,
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
            "message": f"Job did not complete within {wait_timeout} seconds.",
        }

    # ==================== DIRECT ANALYSIS (No MinIO Storage) ====================

    @mcp.tool()
    async def analyze_csv_directly(
        csv_content: str,
        user_id: str,
        target_column: Optional[str] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        📊 Analyze CSV data directly without storing in MinIO.

        Useful for one-time analysis of temporary data.

        Args:
            csv_content: CSV data as string (or base64 if is_base64=True)
            user_id: User ID
            target_column: Optional target for association analysis
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            job_id: Job ID for tracking
            data_preview: Preview of parsed data
        """
        return await stats_client.direct_analyze(
            csv_content=csv_content,
            user_id=user_id,
            target_column=target_column,
            is_base64=is_base64,
        )

    @mcp.tool()
    async def get_quick_stats(
        csv_content: str,
        is_base64: bool = False,
    ) -> dict:
        """
        ⚡ Get quick statistics synchronously (instant results).

        Returns immediately with basic statistics without job queue.

        Args:
            csv_content: CSV data as string
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            rows: Number of rows
            columns: Number of columns
            column_info: Type, nulls, unique count per column
            missing_summary: Missing value statistics
            numeric_summary: Basic stats for numeric columns
        """
        return await stats_client.quick_stats(
            csv_content=csv_content,
            is_base64=is_base64,
        )

    # ==================== ADVANCED ANALYSIS TOOLS ====================

    @mcp.tool()
    async def analyze_correlations(
        csv_content: str,
        columns: Optional[List[str]] = None,
        method: str = "all",
        min_correlation: float = 0.3,
        is_base64: bool = False,
    ) -> dict:
        """
        📈 Enhanced correlation analysis with multiple methods.

        Computes Pearson, Spearman, and Kendall correlations with:
        - Full correlation matrices
        - P-value matrices for significance testing
        - Significant pairs highlighted

        Args:
            csv_content: CSV data as string
            columns: Columns to analyze (default: all numeric)
            method: "pearson", "spearman", "kendall", or "all"
            min_correlation: Minimum |r| to flag (default: 0.3)
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            matrices: Correlation and p-value matrices
            significant_pairs: Pairs with significant correlation
            summary: Overall statistics
        """
        import base64
        from io import StringIO

        import pandas as pd

        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode("utf-8")
            df = pd.read_csv(StringIO(csv_content))

            from ..stats_worker_tasks import compute_enhanced_correlation

            result = compute_enhanced_correlation(df, columns=columns, method=method, min_correlation=min_correlation)
            return {"status": "success", **result.to_dict()}

        except ImportError:
            return await _compute_correlation_fallback(csv_content, columns, is_base64)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def compare_groups(
        csv_content: str,
        numeric_column: str,
        group_column: str,
        is_base64: bool = False,
    ) -> dict:
        """
        🔬 Compare distributions of a numeric variable across groups.

        Automatically selects appropriate tests:
        - 2 groups: t-test or Mann-Whitney U
        - 3+ groups: ANOVA or Kruskal-Wallis + post-hoc

        Args:
            csv_content: CSV data as string
            numeric_column: Column with numeric values to compare
            group_column: Column with group labels
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            groups: Group labels
            normality: Normality test results per group
            variance_test: Levene's test result
            main_test: Main comparison test result
            post_hoc: Pairwise comparisons (if >2 groups)
        """
        import base64
        from io import StringIO

        import pandas as pd

        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode("utf-8")
            df = pd.read_csv(StringIO(csv_content))

            from ..stats_worker_tasks import compare_distributions

            result = compare_distributions(df, numeric_column, group_column)
            return {"status": "success", **result.to_dict()}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def analyze_missing_values(
        csv_content: str,
        is_base64: bool = False,
    ) -> dict:
        """
        🔍 Comprehensive missing value analysis.

        Detects missing value patterns:
        - MCAR (Missing Completely At Random)
        - MAR (Missing At Random)
        - MNAR (Missing Not At Random)

        Args:
            csv_content: CSV data as string
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            summary: Overall missing statistics
            columns: Per-column missing details
            pattern: MCAR/MAR/MNAR with confidence
            recommendations: Handling suggestions
        """
        import base64
        from io import StringIO

        import pandas as pd

        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode("utf-8")
            df = pd.read_csv(StringIO(csv_content))

            from ..stats_worker_tasks import analyze_missing_values as analyze_mv

            result = analyze_mv(df)
            return {"status": "success", **result.to_dict()}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def check_multicollinearity(
        csv_content: str,
        columns: Optional[List[str]] = None,
        vif_threshold: float = 5.0,
        is_base64: bool = False,
    ) -> dict:
        """
        📊 Check multicollinearity using VIF (Variance Inflation Factor).

        VIF interpretation:
        - VIF = 1: No correlation
        - VIF < 5: Acceptable
        - VIF ≥ 5: Problematic
        - VIF ≥ 10: Severe

        Args:
            csv_content: CSV data as string
            columns: Columns to analyze (default: all numeric)
            vif_threshold: VIF threshold for flagging (default: 5.0)
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            vif_results: VIF for each column
            problematic_columns: Columns with high VIF
            recommendations: Action suggestions
        """
        import base64
        from io import StringIO

        import pandas as pd

        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode("utf-8")
            df = pd.read_csv(StringIO(csv_content))

            from ..stats_worker_tasks import compute_vif

            result = compute_vif(df, columns=columns, vif_threshold=vif_threshold)
            return {"status": "success", **result.to_dict()}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def run_full_statistical_analysis(
        csv_content: str,
        target_column: Optional[str] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        🚀 Run complete statistical analysis including all advanced features.

        Combines: correlation, missing values, VIF, group comparisons.

        Args:
            csv_content: CSV data as string
            target_column: Optional target for group analysis
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            correlation_analysis: Full correlation results
            missing_analysis: Missing value patterns
            multicollinearity: VIF analysis
            group_comparisons: Comparisons by target (if applicable)
        """
        import base64
        from io import StringIO

        import pandas as pd

        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode("utf-8")
            df = pd.read_csv(StringIO(csv_content))

            from ..stats_worker_tasks import run_enhanced_analysis

            result = run_enhanced_analysis(
                df, target_column=target_column, include_vif=True, include_missing_analysis=True
            )
            return {"status": "success", **result}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    logger.info("Registered 14 EDA tools")


async def _compute_correlation_fallback(csv_content: str, columns: Optional[List[str]], is_base64: bool) -> dict:
    """Fallback correlation computation without advanced module"""
    import base64
    from io import StringIO

    import pandas as pd

    if is_base64:
        csv_content = base64.b64decode(csv_content).decode("utf-8")
    df = pd.read_csv(StringIO(csv_content))

    if columns:
        numeric_cols = [c for c in columns if c in df.columns]
    else:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if len(numeric_cols) < 2:
        return {"status": "error", "error": "Need at least 2 numeric columns"}

    corr = df[numeric_cols].corr()

    return {
        "status": "success",
        "columns": numeric_cols,
        "pearson_matrix": corr.to_dict(),
        "note": "Basic correlation (advanced module not available)",
    }
