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
from typing import Optional, List

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_statistics_tools(mcp: FastMCP, automl_client) -> None:
    """Register statistics tools with MCP server"""
    
    from .stats_client import StatsClient
    stats_client = StatsClient()
    
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
        
        This is useful for:
        - One-time analysis of temporary data
        - Quick data exploration without permanent storage
        - Testing with small datasets
        
        The CSV content is passed directly and processed without being 
        saved to MinIO. Results are stored temporarily for retrieval.
        
        ⚠️ For large datasets, use register_dataset + auto_analyze instead.
        
        Args:
            csv_content: CSV data as string (or base64 if is_base64=True)
            user_id: User ID
            target_column: Optional target for association analysis
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            job_id: Job ID for tracking
            data_preview: Preview of parsed data (rows, columns, sample)
            
        Example:
            # Analyze temporary data
            analyze_csv_directly(
                csv_content="name,age,score\\nAlice,30,85\\nBob,25,90",
                user_id="user1",
                target_column="score"
            )
        """
        result = await stats_client.direct_analyze(
            csv_content=csv_content,
            user_id=user_id,
            target_column=target_column,
            is_base64=is_base64,
        )
        return result
    
    @mcp.tool()
    async def get_quick_stats(
        csv_content: str,
        is_base64: bool = False,
    ) -> dict:
        """
        ⚡ Get quick statistics synchronously (instant results).
        
        Returns immediately with basic statistics without job queue.
        For full analysis, use analyze_csv_directly instead.
        
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
        result = await stats_client.quick_stats(
            csv_content=csv_content,
            is_base64=is_base64,
        )
        return result
    
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
        - Heatmap data for visualization
        - Significant pairs highlighted
        
        Args:
            csv_content: CSV data as string
            columns: Columns to analyze (default: all numeric)
            method: "pearson", "spearman", "kendall", or "all"
            min_correlation: Minimum |r| to flag (default: 0.3)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            matrices: Pearson/Spearman correlation and p-value matrices
            significant_pairs: Pairs with significant correlation
            heatmap_data: Ready-to-plot heatmap data
            summary: Overall statistics
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            # Parse CSV
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            # Import and run analysis
            from .stats_worker_tasks import compute_enhanced_correlation
            result = compute_enhanced_correlation(
                df, columns=columns, method=method, min_correlation=min_correlation
            )
            return {"status": "success", **result.to_dict()}
            
        except ImportError:
            # Fallback: Direct computation
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
        
        Includes:
        - Normality tests per group
        - Homogeneity of variance (Levene's test)
        - Effect size calculation
        - Post-hoc pairwise comparisons with Bonferroni correction
        
        Args:
            csv_content: CSV data as string
            numeric_column: Column with numeric values to compare
            group_column: Column with group labels
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            groups: Group labels
            normality: Normality test results per group
            variance_test: Levene's test result
            main_test: Main comparison (t-test/ANOVA/etc)
            post_hoc: Pairwise comparisons (if >2 groups)
            group_statistics: Descriptive stats per group
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compare_distributions
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
        - MCAR (Missing Completely At Random): Safe for listwise deletion
        - MAR (Missing At Random): Use model-based imputation
        - MNAR (Missing Not At Random): Complex handling needed
        
        Includes:
        - Per-column missing statistics
        - Little's MCAR test (approximation)
        - Missing value correlations
        - Imputation recommendations
        
        Args:
            csv_content: CSV data as string
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            summary: Overall missing statistics
            columns: Per-column missing details
            pattern: MCAR/MAR/MNAR with confidence
            mcar_test: Little's MCAR test result
            recommendations: Handling suggestions
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import analyze_missing_values as analyze_mv
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
        - VIF = 1: No correlation with other variables
        - VIF < 5: Acceptable (moderate correlation)
        - VIF ≥ 5: High correlation (problematic)
        - VIF ≥ 10: Severe multicollinearity (very problematic)
        
        High VIF indicates that a variable is highly correlated with
        other variables, which can cause problems in regression models.
        
        Args:
            csv_content: CSV data as string
            columns: Columns to analyze (default: all numeric)
            vif_threshold: VIF threshold for flagging (default: 5.0)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            vif_results: VIF for each column
            condition_number: Overall condition number
            problematic_columns: Columns with high VIF
            recommendations: Action suggestions
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compute_vif
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
        
        This is the most comprehensive analysis tool, combining:
        - Basic descriptive statistics
        - Enhanced correlation analysis
        - Missing value pattern detection
        - Multicollinearity check (VIF)
        - Group comparisons (if target is categorical)
        
        Use this for a complete overview of your dataset.
        
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
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import run_enhanced_analysis
            result = run_enhanced_analysis(
                df, target_column=target_column,
                include_vif=True, include_missing_analysis=True
            )
            return {"status": "success", **result}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _compute_correlation_fallback(csv_content: str, columns: Optional[List[str]], is_base64: bool) -> dict:
        """Fallback correlation computation without advanced module"""
        import pandas as pd
        import base64
        from io import StringIO
        from scipy import stats
        
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
        csv_content: str,
        groupby: Optional[str] = None,
        categorical: Optional[List[str]] = None,
        continuous: Optional[List[str]] = None,
        nonnormal: Optional[List[str]] = None,
        pval: bool = True,
        output_format: str = "dict",
        is_base64: bool = False,
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
            csv_content: CSV data as string
            groupby: Column to stratify by (e.g., "treatment_group")
            categorical: Columns to treat as categorical (auto-detect if not specified)
            continuous: Columns to treat as continuous (auto-detect if not specified)
            nonnormal: Columns to report as median[IQR] instead of mean±SD
            pval: Include p-values for group comparisons (default: True)
            output_format: "dict", "markdown", "html", or "latex"
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            status: "success" or "error"
            table_data: Summary statistics table as nested dict
            n_total: Total sample size
            n_groups: Sample size per group (if grouped)
            format: Requested output format
            markdown/html/latex: Formatted table (if format specified)
            tests_used: Statistical tests applied
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            # Parse CSV
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            # Import and run TableOne generation
            from .stats_worker_tasks import generate_tableone
            result = generate_tableone(
                df=df,
                groupby=groupby,
                categorical=categorical,
                continuous=continuous,
                nonnormal=nonnormal,
                include_pval=pval,
            )
            
            # Format output
            response = {
                "status": "success",
                "n_total": result.get("n_total", len(df)),
                "n_groups": result.get("n_groups", {}),
                "variables_analyzed": result.get("variables_analyzed", []),
                "tests_used": result.get("tests_used", {}),
                "format": output_format,
            }
            
            # Add formatted output based on format
            if output_format == "dict":
                response["table_data"] = result.get("table_data", {})
            elif output_format == "markdown":
                response["markdown"] = result.get("markdown", "")
                response["table_data"] = result.get("table_data", {})
            elif output_format == "html":
                response["html"] = result.get("html", "")
                response["table_data"] = result.get("table_data", {})
            elif output_format == "latex":
                response["latex"] = result.get("latex", "")
                response["table_data"] = result.get("table_data", {})
            else:
                response["table_data"] = result.get("table_data", {})
            
            return response
            
        except ImportError:
            return await _generate_tableone_fallback(
                csv_content, groupby, categorical, nonnormal, pval, is_base64
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def get_tableone_preview(
        csv_content: str,
        groupby: Optional[str] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        🔍 Preview Table 1 configuration and column type suggestions.
        
        Analyzes dataset and suggests optimal TableOne configuration:
        - Which columns should be categorical vs continuous
        - Which continuous columns appear non-normal (use median/IQR)
        - Good groupby candidates (2-5 unique values)
        
        Use this before generate_tableone_directly to optimize parameters.
        
        Args:
            csv_content: CSV data as string
            groupby: Proposed groupby column (optional)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            shape: Dataset dimensions
            suggested_categorical: Columns detected as categorical
            suggested_continuous: Columns detected as continuous  
            suggested_nonnormal: Skewed continuous columns
            groupby_candidates: Good columns for stratification
            groupby_info: Info about proposed groupby (if provided)
        """
        import pandas as pd
        import base64
        from io import StringIO
        import numpy as np
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
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
                        except:
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
        import pandas as pd
        import base64
        from io import StringIO
        import numpy as np
        
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
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        time_points: Optional[List[float]] = None,
        alpha: float = 0.05,
        is_base64: bool = False,
    ) -> dict:
        """
        📈 Kaplan-Meier survival analysis with log-rank test.
        
        Performs non-parametric survival analysis:
        - Kaplan-Meier survival curves for each group
        - Median survival time with 95% CI
        - Log-rank test for group comparisons
        - Survival probability at specified time points
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event (e.g., "survival_months")
            event_col: Column name for event indicator (1=event occurred, 0=censored)
            group_col: Optional column for stratification (e.g., "treatment")
            time_points: Specific times to report survival (e.g., [12, 24, 36])
            alpha: Significance level for CI (default: 0.05 for 95% CI)
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            survival_curves: KM curves for each group
            median_survival: Median survival with CI per group
            log_rank_test: Test for difference between groups (if grouped)
            survival_at_times: Survival probability at specified times
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import kaplan_meier_analysis, survival_summary
            
            # Get KM analysis
            km_result = kaplan_meier_analysis(
                df, time_col, event_col, group_col, alpha
            )
            
            # Get summary with time points
            summary = survival_summary(
                df, time_col, event_col, group_col, time_points
            )
            
            return {
                "status": "success",
                **km_result,
                "summary": summary,
            }
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def cox_proportional_hazards(
        csv_content: str,
        time_col: str,
        event_col: str,
        covariates: Optional[List[str]] = None,
        alpha: float = 0.05,
        is_base64: bool = False,
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
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            covariates: List of covariate columns (default: all numeric)
            alpha: Significance level for CI
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            coefficients: Beta coefficients with SE, HR, CI, p-value
            model_fit: Log-likelihood, concordance index
            global_tests: Wald test, likelihood ratio test
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import cox_regression
            
            result = cox_regression(
                df, time_col, event_col, covariates, alpha
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def compare_survival(
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: str,
        is_base64: bool = False,
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
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Column for group stratification
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            groups: Survival statistics per group
            log_rank_test: Test for overall difference
            pairwise_comparisons: Tests between each pair (if >2 groups)
            conclusion: Interpretation of results
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import compare_survival_curves
            
            result = compare_survival_curves(
                df, time_col, event_col, group_col
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    @mcp.tool()
    async def survival_data_summary(
        csv_content: str,
        time_col: str,
        event_col: str,
        group_col: Optional[str] = None,
        time_points: Optional[List[float]] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        📋 Get summary statistics for survival data.
        
        Quick overview of survival dataset:
        - Number of subjects, events, censored
        - Follow-up time distribution
        - Median survival per group
        - Event rates
        
        Args:
            csv_content: CSV data as string
            time_col: Column name for time-to-event
            event_col: Column name for event indicator
            group_col: Optional grouping column
            time_points: Times to report survival (e.g., [12, 24, 36])
            is_base64: Set True if csv_content is base64 encoded
        
        Returns:
            n_subjects: Total sample size
            n_events: Number of events
            n_censored: Number censored
            follow_up: Follow-up time statistics
            by_group: Statistics per group (if grouped)
        """
        import pandas as pd
        import base64
        from io import StringIO
        
        try:
            if is_base64:
                csv_content = base64.b64decode(csv_content).decode('utf-8')
            df = pd.read_csv(StringIO(csv_content))
            
            from .stats_worker_tasks import survival_summary
            
            result = survival_summary(
                df, time_col, event_col, group_col, time_points
            )
            
            return {"status": "success", **result}
            
        except ImportError:
            return {"status": "error", "error": "Survival analysis module not available"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    logger.info("Registered 25 statistics tools (including advanced analysis + TableOne + Survival)")

