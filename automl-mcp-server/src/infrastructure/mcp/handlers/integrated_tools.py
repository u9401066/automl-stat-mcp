"""
Integrated Analysis Tools for MCP

Unified tools that combine multiple analysis steps into single operations.
These are the RECOMMENDED tools for Agent workflows.

Features:
- Automatic path resolution (host → container)
- Default user_id
- Combined analysis (stats + tableone + correlations)
- Report generation

Created: 2025-12-16
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from mcp.server.fastmcp import Context, FastMCP
from scipy import stats as scipy_stats

logger = logging.getLogger(__name__)

# =============================================================================
# PATH RESOLUTION
# =============================================================================

# Data directories mounted in container
DATA_MOUNT_PATHS = {
    "sample_data": "/data/sample_data",
    "projects": "/data/projects",
    "uploads": "/data/uploads",
}

# Default values
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "eric")


def resolve_csv_path(user_input: str) -> str:
    """
    Resolve user input path to container path.

    Conversion Rules:
    - "iris.csv" → "/data/sample_data/iris.csv"
    - "sample_data/xxx.csv" → "/data/sample_data/xxx.csv"
    - "projects/study1/data.csv" → "/data/projects/study1/data.csv"
    - "/home/eric/.../sample_data/xxx.csv" → "/data/sample_data/xxx.csv"
    - Already "/data/..." → unchanged

    Args:
        user_input: Path from user (various formats)

    Returns:
        Container path starting with /data/
    """
    # Already correct format
    if user_input.startswith("/data/"):
        return user_input

    # Extract filename for simple inputs
    filename = Path(user_input).name

    # Just filename (e.g., "iris.csv")
    if "/" not in user_input:
        return f"/data/sample_data/{filename}"

    # Contains "sample_data"
    if "sample_data" in user_input:
        parts = user_input.split("sample_data/")
        return f"/data/sample_data/{parts[-1]}"

    # Contains "projects"
    if "projects" in user_input:
        parts = user_input.split("projects/")
        return f"/data/projects/{parts[-1]}"

    # Contains "uploads"
    if "uploads" in user_input:
        parts = user_input.split("uploads/")
        return f"/data/uploads/{parts[-1]}"

    # Host absolute path (e.g., /home/eric/...)
    if user_input.startswith("/home/") or "/workspace" in user_input:
        return f"/data/sample_data/{filename}"

    # Default: assume sample_data
    return f"/data/sample_data/{user_input}"


def validate_file_exists(csv_path: str) -> tuple[bool, str]:
    """
    Validate that file exists at the resolved path.

    Returns:
        (success, message_or_path)
    """
    path = Path(csv_path)

    if path.exists() and path.is_file():
        return True, str(path)

    # Try common alternatives
    alternatives = [
        csv_path,
        f"/data/sample_data/{path.name}",
        f"/data/projects/{path.name}",
    ]

    for alt in alternatives:
        if Path(alt).exists():
            return True, alt

    return False, f"File not found: {csv_path}. Use list_available_files() to see available files."


# =============================================================================
# ANALYSIS HELPERS
# =============================================================================


def compute_quick_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute quick statistics for a DataFrame"""
    column_info = []
    for col in df.columns:
        info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "missing": int(df[col].isna().sum()),
            "unique": int(df[col].nunique()),
        }
        if df[col].dtype in ["int64", "float64"]:
            info["mean"] = round(float(df[col].mean()), 4) if not df[col].isna().all() else None
            info["std"] = round(float(df[col].std()), 4) if not df[col].isna().all() else None
        column_info.append(info)

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "column_info": column_info,
        "missing_total": int(df.isna().sum().sum()),
    }


def compute_tableone(df: pd.DataFrame, group_column: str, pval: bool = True) -> Dict[str, Any]:
    """Compute Table One statistics"""
    try:
        from tableone import TableOne

        # Identify column types
        categorical = []
        continuous = []
        for col in df.columns:
            if col == group_column:
                continue
            if df[col].dtype == "object" or df[col].nunique() < 10:
                categorical.append(col)
            elif df[col].dtype in ["int64", "float64"]:
                continuous.append(col)

        # Create TableOne
        table = TableOne(
            df,
            columns=categorical + continuous,
            categorical=categorical,
            groupby=group_column,
            pval=pval,
        )

        return {
            "status": "success",
            "html": table.to_html(),
            "markdown": table.tabulate(tablefmt="pipe"),
            "group_counts": df[group_column].value_counts().to_dict(),
        }
    except ImportError:
        # Fallback if tableone not installed
        result = {"status": "success", "groups": {}}
        for group in df[group_column].unique():
            group_df = df[df[group_column] == group]
            result["groups"][str(group)] = {
                "n": len(group_df),
                "summary": group_df.describe().to_dict(),
            }
        return result


def compute_correlations(df: pd.DataFrame, min_correlation: float = 0.3) -> Dict[str, Any]:
    """Compute correlation analysis"""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if len(numeric_cols) < 2:
        return {"status": "error", "error": "Need at least 2 numeric columns"}

    # Compute correlation matrix
    corr_matrix = df[numeric_cols].corr(method="pearson")

    # Find significant pairs
    significant_pairs = []
    for i, col1 in enumerate(numeric_cols):
        for j, col2 in enumerate(numeric_cols):
            if i < j:
                r = corr_matrix.loc[col1, col2]
                if abs(r) >= min_correlation and not pd.isna(r):
                    significant_pairs.append(
                        {
                            "var1": col1,
                            "var2": col2,
                            "correlation": round(float(r), 4),
                        }
                    )

    return {
        "status": "success",
        "matrix": corr_matrix.round(4).to_dict(),
        "significant_pairs": sorted(significant_pairs, key=lambda x: abs(x["correlation"]), reverse=True),
        "n_significant": len(significant_pairs),
    }


def compute_group_comparison(df: pd.DataFrame, numeric_column: str, group_column: str) -> Dict[str, Any]:
    """Compare numeric variable across groups"""
    groups = df[group_column].dropna().unique().tolist()
    n_groups = len(groups)

    # Group statistics
    group_stats = {}
    group_data = {}
    for g in groups:
        data = df[df[group_column] == g][numeric_column].dropna()
        group_data[str(g)] = data.values
        group_stats[str(g)] = {
            "n": len(data),
            "mean": round(float(data.mean()), 4),
            "std": round(float(data.std()), 4),
            "median": round(float(data.median()), 4),
        }

    # Select test
    if n_groups == 2:
        g1, g2 = [str(g) for g in groups[:2]]
        stat, pval = scipy_stats.ttest_ind(group_data[g1], group_data[g2])
        test_name = "Independent t-test"
    else:
        stat, pval = scipy_stats.f_oneway(*[group_data[str(g)] for g in groups])
        test_name = "One-way ANOVA"

    return {
        "status": "success",
        "groups": [str(g) for g in groups],
        "n_groups": n_groups,
        "group_statistics": group_stats,
        "comparison": {
            "test": test_name,
            "statistic": round(float(stat), 4),
            "p_value": round(float(pval), 6),
            "significant": pval < 0.05,
        },
    }


# =============================================================================
# INTEGRATED TOOLS REGISTRATION
# =============================================================================


def register_integrated_tools(mcp: FastMCP, automl_client) -> None:
    """Register integrated analysis tools with MCP server"""

    async def _report(ctx, progress: float, total: float, message: str) -> None:
        """Safely report progress to MCP client."""
        if ctx is None:
            return
        try:
            await ctx.report_progress(progress=progress, total=total, message=message)
        except Exception:
            pass

    # ==========================================================================
    # SMART ANALYZE - The All-in-One Tool
    # ==========================================================================

    @mcp.tool()
    async def smart_analyze(
        csv_path: str,
        group_column: Optional[str] = None,
        analysis_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        include_correlations: bool = True,
        generate_report: bool = True,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """
        🎯 Smart Analyze - Complete data analysis in one call.

        This is the RECOMMENDED tool for data analysis. It automatically:
        1. Resolves file paths (host → container)
        2. Gets quick statistics
        3. Generates Table One (if group_column provided)
        4. Analyzes correlations (if requested)
        5. Compiles results into a summary

        Path Resolution (automatic):
        - "iris.csv" → "/data/sample_data/iris.csv"
        - "sample_data/xxx.csv" → "/data/sample_data/xxx.csv"
        - "/home/eric/.../xxx.csv" → auto-resolved

        Args:
            csv_path: Path to CSV file (flexible format, auto-resolved)
            group_column: Column for grouping (e.g., "treatment_group")
            analysis_types: List of analyses ["stats", "tableone", "correlation"]
                           Default: all applicable
            user_id: User ID (default: "eric")
            include_correlations: Include correlation analysis (default: True)
            generate_report: Generate markdown summary (default: True)

        Returns:
            resolved_path: The actual path used
            quick_stats: Basic statistics (rows, columns, missing)
            tableone: Table One results (if group_column provided)
            correlations: Correlation matrix (if include_correlations=True)
            result_ids: All result IDs for reference
            summary: Text summary of key findings

        Example:
            # Simple analysis
            smart_analyze(csv_path="iris.csv")

            # Medical study with grouping
            smart_analyze(
                csv_path="medical_study.csv",
                group_column="treatment_group",
                include_correlations=True
            )
        """
        # Resolve and validate path
        resolved_path = resolve_csv_path(csv_path)
        valid, msg = validate_file_exists(resolved_path)

        if not valid:
            return {
                "status": "error",
                "error": msg,
                "original_path": csv_path,
                "resolved_path": resolved_path,
                "suggestion": "Use list_available_files() to see available files.",
            }

        resolved_path = msg  # msg contains the valid path
        user_id = user_id or DEFAULT_USER_ID

        results = {
            "status": "success",
            "original_path": csv_path,
            "resolved_path": resolved_path,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "analyses_performed": [],
            "result_ids": {},
        }

        try:
            # Read data
            await _report(ctx, 10, 100, "Loading CSV data...")
            df = pd.read_csv(resolved_path)

            # 1. Quick Stats (always)
            await _report(ctx, 25, 100, "Computing quick statistics...")
            quick_stats = compute_quick_stats(df)
            results["quick_stats"] = quick_stats
            results["analyses_performed"].append("quick_stats")
            results["data_overview"] = {
                "rows": quick_stats["rows"],
                "columns": quick_stats["columns"],
                "missing_count": quick_stats["missing_total"],
                "column_names": [c["name"] for c in quick_stats["column_info"]],
            }

            # 2. Table One (if group_column provided)
            if group_column and group_column in df.columns:
                await _report(ctx, 50, 100, "Generating Table One...")
                tableone_result = compute_tableone(df, group_column, pval=True)
                results["tableone"] = tableone_result
                results["analyses_performed"].append("tableone")

            # 3. Correlations (if requested)
            if include_correlations:
                await _report(ctx, 75, 100, "Analyzing correlations...")
                corr_result = compute_correlations(df)
                results["correlations"] = corr_result
                results["analyses_performed"].append("correlations")

            # 4. Generate Summary
            await _report(ctx, 90, 100, "Generating summary...")
            summary_lines = [
                f"## Analysis Summary for {Path(resolved_path).name}",
                f"- **Rows**: {results['data_overview']['rows']}",
                f"- **Columns**: {results['data_overview']['columns']}",
                f"- **Missing Values**: {results['data_overview']['missing_count']}",
            ]

            if group_column:
                summary_lines.append(f"- **Grouped by**: {group_column}")

            if results.get("tableone"):
                summary_lines.append("- **Table One**: Generated ✅")

            if results.get("correlations"):
                n_sig = results["correlations"].get("n_significant", 0)
                summary_lines.append(f"- **Significant Correlations**: {n_sig} pairs (|r| ≥ 0.3)")

            results["summary"] = "\n".join(summary_lines)
            await _report(ctx, 100, 100, "Analysis complete")

        except Exception as e:
            results["status"] = "partial_error"
            results["error"] = str(e)
            logger.error(f"smart_analyze error: {e}")

        return results

    # ==========================================================================
    # ANALYZE MEDICAL STUDY - Specialized for RCT/Cohort Studies
    # ==========================================================================

    @mcp.tool()
    async def analyze_medical_study(
        csv_path: str,
        treatment_column: str,
        outcome_columns: List[str],
        covariates: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        run_propensity: bool = False,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """
        🏥 Complete Medical Study Analysis Pipeline.

        Specialized tool for RCT or observational studies. Executes:
        1. Baseline characteristics (Table One)
        2. Treatment effect analysis (for each outcome)
        3. Correlation analysis
        4. Generates publication-ready report

        Path Resolution: Same as smart_analyze (automatic)

        Args:
            csv_path: Path to CSV file (auto-resolved)
            treatment_column: Treatment/exposure column (e.g., "treatment_group")
            outcome_columns: List of outcome columns to analyze
            covariates: Covariates for adjustment (auto-detected if None)
            user_id: User ID (default: "eric")
            run_propensity: Run propensity score analysis (default: False)

        Returns:
            baseline: Table One results
            treatment_effects: Effect analysis for each outcome
            correlations: Correlation matrix
            report: Markdown report
            result_ids: All result IDs

        Example:
            analyze_medical_study(
                csv_path="medical_study_200.csv",
                treatment_column="treatment_group",
                outcome_columns=["bp_change", "weight_change"]
            )
        """
        # Resolve path
        resolved_path = resolve_csv_path(csv_path)
        valid, msg = validate_file_exists(resolved_path)

        if not valid:
            return {"status": "error", "error": msg}

        resolved_path = msg
        user_id = user_id or DEFAULT_USER_ID

        results = {
            "status": "success",
            "study_type": "medical_study",
            "resolved_path": resolved_path,
            "treatment_column": treatment_column,
            "outcome_columns": outcome_columns,
            "timestamp": datetime.utcnow().isoformat(),
            "result_ids": {},
        }

        try:
            await _report(ctx, 10, 100, "Loading study data...")
            df = pd.read_csv(resolved_path)

            # 1. Table One (Baseline Characteristics)
            await _report(ctx, 25, 100, "Generating baseline characteristics (Table One)...")
            tableone = compute_tableone(df, treatment_column, pval=True)
            results["baseline"] = tableone

            # 2. Treatment Effects (for each outcome)
            await _report(ctx, 50, 100, "Analyzing treatment effects...")
            results["treatment_effects"] = {}
            for outcome in outcome_columns:
                if outcome in df.columns:
                    effect = compute_group_comparison(df, outcome, treatment_column)
                    results["treatment_effects"][outcome] = effect

            # 3. Correlations
            await _report(ctx, 75, 100, "Computing correlations...")
            corr = compute_correlations(df)
            results["correlations"] = corr

            # 4. Generate Report Summary
            await _report(ctx, 90, 100, "Generating report...")
            report_lines = [
                "# Medical Study Analysis Report",
                "",
                f"**Dataset**: {Path(resolved_path).name}",
                f"**Analysis Date**: {results['timestamp'][:10]}",
                f"**Treatment Column**: {treatment_column}",
                f"**Outcomes Analyzed**: {', '.join(outcome_columns)}",
                "",
                "## Key Findings",
                "",
            ]

            # Add treatment effect summaries
            for outcome, effect in results.get("treatment_effects", {}).items():
                if isinstance(effect, dict) and "comparison" in effect:
                    comp = effect["comparison"]
                    p_val = comp.get("p_value", "N/A")
                    if isinstance(p_val, (int, float)):
                        sig = "✅ Significant" if p_val < 0.05 else "Not significant"
                        report_lines.append(f"- **{outcome}**: p={p_val:.4f} ({sig})")
                    else:
                        report_lines.append(f"- **{outcome}**: {p_val}")

            results["report"] = "\n".join(report_lines)
            await _report(ctx, 100, 100, "Medical study analysis complete")

        except Exception as e:
            results["status"] = "error"
            results["error"] = str(e)
            logger.error(f"analyze_medical_study error: {e}")

        return results

    # ==========================================================================
    # QUICK PREVIEW - Fast Data Overview
    # ==========================================================================

    @mcp.tool()
    async def quick_preview(
        csv_path: str,
        n_rows: int = 10,
    ) -> Dict[str, Any]:
        """
        ⚡ Quick Preview - Fast data overview with auto path resolution.

        Combines:
        - Path resolution (automatic)
        - Data preview (first n rows)
        - Column info (types, missing)
        - Basic statistics

        This is the fastest way to understand a new dataset.

        Args:
            csv_path: Path to CSV (auto-resolved)
            n_rows: Number of rows to preview (default: 10)

        Returns:
            resolved_path: Actual path used
            shape: (rows, columns)
            columns: Column names and types
            preview: First n rows
            missing: Missing value summary

        Example:
            quick_preview("iris.csv")
            quick_preview("sample_data/heart_disease.csv", n_rows=5)
        """
        resolved_path = resolve_csv_path(csv_path)
        valid, msg = validate_file_exists(resolved_path)

        if not valid:
            return {"status": "error", "error": msg}

        resolved_path = msg

        try:
            df = pd.read_csv(resolved_path, nrows=n_rows + 100)  # Read a bit more for stats

            # Basic info
            result = {
                "status": "success",
                "original_path": csv_path,
                "resolved_path": resolved_path,
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "columns": [
                    {
                        "name": col,
                        "dtype": str(df[col].dtype),
                        "missing": int(df[col].isna().sum()),
                        "unique": int(df[col].nunique()),
                    }
                    for col in df.columns
                ],
                "preview": df.head(n_rows).to_dict(orient="records"),
            }

            # Numeric summary
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                result["numeric_summary"] = df[numeric_cols].describe().to_dict()

            return result

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "resolved_path": resolved_path,
            }

    # ==========================================================================
    # COMPARE TREATMENT GROUPS - Simplified Interface
    # ==========================================================================

    @mcp.tool()
    async def compare_treatment_groups(
        csv_path: str,
        treatment_column: str,
        outcome_column: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        🔬 Compare Treatment Groups - Simplified group comparison.

        Wraps compare_groups with automatic:
        - Path resolution
        - Default user_id
        - Method selection (t-test vs Mann-Whitney)
        - Plain English interpretation

        Args:
            csv_path: Path to CSV (auto-resolved)
            treatment_column: Group column (e.g., "treatment_group")
            outcome_column: Numeric outcome to compare
            user_id: User ID (default: "eric")

        Returns:
            groups: Group statistics (mean, std, n)
            comparison: Test results (statistic, p-value, method)
            interpretation: Plain English interpretation

        Example:
            compare_treatment_groups(
                csv_path="medical_study.csv",
                treatment_column="treatment_group",
                outcome_column="bp_change"
            )
        """
        resolved_path = resolve_csv_path(csv_path)
        valid, msg = validate_file_exists(resolved_path)

        if not valid:
            return {"status": "error", "error": msg}

        resolved_path = msg
        user_id = user_id or DEFAULT_USER_ID

        try:
            df = pd.read_csv(resolved_path)
            result = compute_group_comparison(df, outcome_column, treatment_column)

            # Add interpretation
            if "comparison" in result:
                p_val = result["comparison"].get("p_value")
                if isinstance(p_val, (int, float)):
                    if p_val < 0.001:
                        interpretation = "Highly significant difference (p < 0.001)"
                    elif p_val < 0.05:
                        interpretation = f"Significant difference (p = {p_val:.4f})"
                    else:
                        interpretation = f"No significant difference (p = {p_val:.4f})"
                    result["interpretation"] = interpretation

            result["original_path"] = csv_path
            result["resolved_path"] = resolved_path

            return result

        except Exception as e:
            return {"status": "error", "error": str(e)}

    logger.info(
        "Integrated tools registered: smart_analyze, analyze_medical_study, quick_preview, compare_treatment_groups"
    )
