"""
TableOne Tools Module - Publication-Ready Summary Tables

This module provides MCP tools for generating publication-quality
Table 1 (baseline characteristics) for medical research.

Tools:
    - submit_tableone_job: Submit async TableOne generation job
    - run_quick_tableone: Quick TableOne with smart defaults
    - get_column_suggestions: Get column type suggestions
    - generate_tableone_directly: Direct CSV to TableOne
    - get_tableone_preview: Preview configuration suggestions
"""
import base64
import time
from io import StringIO
from typing import List, Optional

import numpy as np
import pandas as pd

from .base import logger


def register_tableone_tools(mcp, stats_client):
    """Register all TableOne-related MCP tools."""
    
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
            logger.error(f"generate_tableone_directly error: {e}")
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
                        except Exception:
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
            logger.error(f"get_tableone_preview error: {e}")
            return {"status": "error", "error": str(e)}
    
    # Helper function for fallback
    async def _generate_tableone_fallback(
        csv_content: str,
        groupby: Optional[str],
        categorical: Optional[List[str]],
        nonnormal: Optional[List[str]],
        pval: bool,
        is_base64: bool,
    ) -> dict:
        """Fallback TableOne generation without advanced module"""
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
    
    logger.info("TableOne tools registered: 5 tools")
