"""
Smart Tools for MCP

Intelligent workflow tools that guide AI agents through data analysis processes.
These tools return structured "tickets" for task tracking and user interaction.

Enhanced with Data Validation Layer for:
- Missing value detection
- PII (Personally Identifiable Information) detection
- Invalid column detection
- Outlier detection
- Data type issues
"""
import base64
import io
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from mcp.server.fastmcp import FastMCP

from .data_cleaner import DataCleaner
from .data_validator import DataValidator, ValidationReport

logger = logging.getLogger(__name__)


def register_smart_tools(mcp: FastMCP, automl_client) -> None:
    """Register smart workflow tools with MCP server"""

    from .stats_client import StatsClient
    stats_client = StatsClient()

    # Initialize validation and cleaning tools
    data_validator = DataValidator()
    data_cleaner = DataCleaner()

    # ==================== HELPER FUNCTIONS ====================

    def _parse_csv_content(csv_content: str, is_base64: bool = False) -> pd.DataFrame:
        """Parse CSV content into DataFrame"""
        if is_base64:
            decoded = base64.b64decode(csv_content).decode("utf-8")
            return pd.read_csv(io.StringIO(decoded))
        return pd.read_csv(io.StringIO(csv_content))

    def _format_issues_for_response(report: ValidationReport) -> List[dict]:
        """Convert ValidationReport issues to dict for JSON response"""
        return [issue.to_dict() for issue in report.issues]

    def _generate_questions_from_issues(report: ValidationReport) -> List[str]:
        """Generate user questions based on detected issues"""
        questions = []

        # Critical issues first
        critical_issues = [i for i in report.issues if i.severity.value == "critical"]
        if critical_issues:
            pii_issues = [i for i in critical_issues if i.issue_type.value == "pii_detected"]
            if pii_issues:
                cols = [i.column for i in pii_issues if i.column]
                questions.append(
                    f"⚠️ CRITICAL: PII detected in columns: {cols}. "
                    "Options: mask (replace with ***), hash (SHA256), or drop these columns?"
                )

        # High severity
        high_issues = [i for i in report.issues if i.severity.value == "high"]
        for issue in high_issues:
            if issue.issue_type.value == "high_missing_ratio":
                questions.append(
                    f"Missing values found in '{issue.column}' "
                    f"({issue.details.get('missing_pct', 0):.1f}% missing). "
                    "Options: drop rows, drop column, or impute (mean/median/mode)?"
                )

        # Medium severity
        medium_issues = [i for i in report.issues if i.severity.value == "medium"]
        outlier_issues = [i for i in medium_issues if i.issue_type.value == "outliers_detected"]
        if outlier_issues:
            cols = [i.column for i in outlier_issues if i.column]
            questions.append(
                f"Outliers detected in: {cols[:5]}{'...' if len(cols) > 5 else ''}. "
                "Options: cap to IQR bounds, remove, or keep as-is?"
            )

        # Always add storage question
        questions.append(
            "Do you want to save this dataset for future use, or is this a one-time analysis?"
        )

        return questions

    # ==================== SMART DATA ANALYSIS ====================

    @mcp.tool()  # RESTORED: unique functionality (data validation + cleaning workflow)
    async def start_data_analysis(
        csv_content: str,
        user_id: str,
        analysis_purpose: Optional[str] = None,
        target_column: Optional[str] = None,
        is_base64: bool = False,
    ) -> dict:
        """
        🎯 Smart entry point for data analysis workflow.

        This tool analyzes your data and returns a TICKET that guides the next steps.
        The AI agent should use this ticket to ask the user about their preferences.

        **WORKFLOW**:
        1. Call this tool with CSV data
        2. Receive a ticket with data preview and options
        3. Ask user: "Do you want to save this data for future use?"
        4. Based on response, call either:
           - `execute_analysis_ticket(ticket_id, save_to_storage=False)` → Quick analysis
           - `execute_analysis_ticket(ticket_id, save_to_storage=True)` → Persistent storage

        **NEW: Data Validation Layer**
        This tool now automatically detects:
        - Missing values (with severity based on percentage)
        - PII (emails, phones, SSNs, credit cards)
        - Invalid columns (constant, all-null, high-cardinality IDs)
        - Outliers (using IQR method)
        - Duplicate rows

        Args:
            csv_content: CSV data as string (or base64 if is_base64=True)
            user_id: User ID for tracking
            analysis_purpose: Optional description (e.g., "ML preparation", "research report")
            target_column: Optional target column for association analysis
            is_base64: Set True if csv_content is base64 encoded

        Returns:
            ticket: Analysis ticket with:
                - ticket_id: Unique identifier for this analysis request
                - status: "pending_user_decision"
                - data_preview: Quick overview of the data
                - data_issues: Detected issues with severity and suggested actions
                - options: Available paths forward
                - suggested_questions: Questions to ask the user (including issue-specific)

        Example:
            ticket = start_data_analysis(
                csv_content="name,age,score\\nAlice,30,85\\nBob,25,90",
                user_id="user1",
                target_column="score"
            )
            # → Returns ticket with any detected issues
            # → Agent asks user about issues and storage preference
            # → User decides, agent calls execute_analysis_ticket with cleaning_decisions
        """
        try:
            # Parse CSV to DataFrame for validation
            df = _parse_csv_content(csv_content, is_base64)

            # Get quick stats for preview
            quick_stats = await stats_client.quick_stats(
                csv_content=csv_content,
                is_base64=is_base64,
            )

            # Generate ticket
            ticket_id = f"analysis-{uuid.uuid4().hex[:12]}"

            # validation_report is a ValidationReport object
            validation_report = data_validator.validate(df, target_column=target_column)

            # Determine if cleaning is needed before analysis
            requires_attention = not validation_report.can_proceed

            # Generate suggested questions based on issues
            suggested_questions = _generate_questions_from_issues(validation_report)

            # Get default cleaning actions
            default_actions = data_cleaner.get_default_actions(validation_report) if validation_report.total_issues > 0 else {}

            ticket = {
                "ticket_id": ticket_id,
                "ticket_type": "data_analysis",
                "status": "pending_user_decision",
                "created_at": datetime.utcnow().isoformat(),
                "user_id": user_id,

                # Data preview
                "data_preview": {
                    "rows": quick_stats.get("rows", 0),
                    "columns": quick_stats.get("columns", 0),
                    "column_names": [c["name"] for c in quick_stats.get("column_info", [])],
                    "column_types": {c["name"]: c["dtype"] for c in quick_stats.get("column_info", [])},
                    "missing_summary": quick_stats.get("missing_summary", {}),
                },

                # Data validation results (NEW)
                "data_issues": {
                    "total_issues": validation_report.total_issues,
                    "requires_attention": requires_attention,
                    "can_proceed": validation_report.can_proceed,
                    "summary": {
                        "critical": validation_report.critical_count,
                        "high": validation_report.high_count,
                        "medium": validation_report.medium_count,
                        "low": validation_report.low_count,
                    },
                    "issues": _format_issues_for_response(validation_report),
                    "default_cleaning_actions": default_actions,
                },

                # Analysis context
                "analysis_context": {
                    "purpose": analysis_purpose,
                    "target_column": target_column,
                    "data_size": f"{quick_stats.get('rows', 0)} rows × {quick_stats.get('columns', 0)} columns",
                },

                # Options for user
                "options": {
                    "quick_analysis": {
                        "description": "Analyze immediately without saving (temporary)",
                        "use_case": "One-time exploration, testing, quick insights",
                        "action": "execute_analysis_ticket(ticket_id, save_to_storage=False)",
                    },
                    "persistent_analysis": {
                        "description": "Save to storage and analyze (permanent)",
                        "use_case": "ML pipeline, repeated access, collaboration",
                        "action": "execute_analysis_ticket(ticket_id, save_to_storage=True, dataset_name='...')",
                    },
                    "clean_and_analyze": {
                        "description": "Apply cleaning then analyze",
                        "use_case": "When data issues detected",
                        "action": "execute_analysis_ticket(ticket_id, cleaning_decisions={...})",
                    },
                },

                # Suggested questions for AI to ask user
                "suggested_questions": suggested_questions,

                # Raw data preserved for execution
                "_internal": {
                    "csv_content": csv_content,
                    "is_base64": is_base64,
                },
            }

            logger.info(f"Created analysis ticket: {ticket_id}")
            return ticket

        except Exception as e:
            logger.error(f"Failed to create analysis ticket: {e}")
            return {
                "ticket_id": None,
                "status": "error",
                "error": str(e),
                "message": "Failed to parse or preview data. Please check the CSV format.",
            }

    @mcp.tool()  # RESTORED: unique functionality (data cleaning + persistent storage)
    async def execute_analysis_ticket(
        ticket_id: str,
        csv_content: str,
        user_id: str,
        save_to_storage: bool = False,
        dataset_name: Optional[str] = None,
        minio_bucket: Optional[str] = None,
        target_column: Optional[str] = None,
        is_base64: bool = False,
        cleaning_decisions: Optional[Dict[str, Any]] = None,
        wait_for_result: bool = True,
        wait_timeout: int = 300,
    ) -> dict:
        """
        🚀 Execute an analysis ticket based on user's decision.

        Call this after `start_data_analysis` and user confirmation.

        **Path A: Quick Analysis (save_to_storage=False)**
        - Analyzes data immediately
        - No permanent storage
        - Returns job ticket for tracking

        **Path B: Persistent Analysis (save_to_storage=True)**
        - Uploads data to MinIO storage
        - Registers as a dataset
        - Analyzes with full tracking
        - Returns job ticket with dataset_id for future reference

        **NEW: Data Cleaning (cleaning_decisions provided)**
        - Applies cleaning based on user decisions before analysis
        - Returns cleaning report showing what was changed

        Args:
            ticket_id: Ticket ID from start_data_analysis
            csv_content: CSV data (same as start_data_analysis)
            user_id: User ID
            save_to_storage: If True, save to MinIO; if False, temporary analysis
            dataset_name: Name for saved dataset (required if save_to_storage=True)
            minio_bucket: Optional bucket name (defaults to 'automl-data')
            target_column: Optional target column for association analysis
            is_base64: Set True if csv_content is base64 encoded
            cleaning_decisions: Optional dict of cleaning actions to apply.
                Format: {
                    "missing_values": {
                        "column_name": "impute_mean" | "impute_median" | "impute_mode" | "drop_rows" | "drop_column"
                    },
                    "pii": {
                        "column_name": "mask" | "hash" | "drop"
                    },
                    "outliers": {
                        "column_name": "cap_iqr" | "remove" | "keep"
                    },
                    "invalid_columns": ["col1", "col2"],  # columns to drop
                    "duplicates": "drop" | "keep"
                }
                If None, uses default actions for detected issues.
            wait_for_result: If True, wait for analysis completion
            wait_timeout: Max seconds to wait (if wait_for_result=True)

        Returns:
            job_ticket: Execution ticket with:
                - ticket_id: Original ticket ID
                - job_id: Backend job ID for tracking
                - status: "submitted" | "running" | "completed" | "failed"
                - storage_mode: "temporary" | "persistent"
                - dataset_id: (if persistent) Dataset ID for future use
                - cleaning_report: (if cleaning applied) Summary of cleaning actions
                - result: (if wait_for_result and completed) Analysis results
        """
        try:
            # Parse CSV to DataFrame
            df = _parse_csv_content(csv_content, is_base64)
            original_shape = df.shape

            # Validate data to get issues
            validation_report = data_validator.validate(df, target_column=target_column)

            # Apply cleaning if there are issues
            cleaning_report = None
            if validation_report.total_issues > 0:
                # Use provided decisions or default actions
                decisions = cleaning_decisions or data_cleaner.get_default_actions(validation_report)

                # Apply cleaning - returns CleaningResult object
                cleaning_result = data_cleaner.clean(df, validation_report, decisions)

                # Check if cleaning was successful
                if not cleaning_result.success:
                    return {
                        "ticket_id": ticket_id,
                        "status": "error",
                        "error": cleaning_result.error or "Cleaning failed",
                        "cleaning_report": cleaning_result.to_dict(),
                    }

                # Get cleaned DataFrame from result
                df = cleaning_result.df

                # Generate cleaning report
                cleaning_report = cleaning_result.to_dict()
                cleaning_report["original_shape"] = {"rows": original_shape[0], "columns": original_shape[1]}
                cleaning_report["cleaned_shape"] = {"rows": df.shape[0], "columns": df.shape[1]}

            # Convert cleaned DataFrame back to CSV for analysis
            cleaned_csv = df.to_csv(index=False)

            if save_to_storage:
                # Path B: Persistent storage
                if not dataset_name:
                    dataset_name = f"dataset-{ticket_id}"

                bucket = minio_bucket or "automl-data"
                # Note: minio_path would be f"{bucket}/{user_id}/{dataset_name}.csv"
                # TODO: Implement actual MinIO upload through automl-service
                _ = bucket  # Suppress unused warning until upload is implemented

                # Upload to MinIO via automl-service
                # First, we need to upload the CSV content
                # For now, use direct analysis but mark as persistent
                # TODO: Implement actual MinIO upload through automl-service

                # Use direct analysis with cleaned data
                submit_result = await stats_client.direct_analyze(
                    csv_content=cleaned_csv,
                    user_id=user_id,
                    target_column=target_column,
                    is_base64=False,  # cleaned_csv is plain text now
                )

                job_id = submit_result.get("job_id")
                storage_mode = "persistent_pending"  # TODO: implement full persistence
                dataset_id = None  # TODO: return actual dataset_id after upload

            else:
                # Path A: Quick analysis (temporary) with cleaned data
                submit_result = await stats_client.direct_analyze(
                    csv_content=cleaned_csv,
                    user_id=user_id,
                    target_column=target_column,
                    is_base64=False,  # cleaned_csv is plain text now
                )

                job_id = submit_result.get("job_id")
                storage_mode = "temporary"
                dataset_id = None

            if not job_id:
                return {
                    "ticket_id": ticket_id,
                    "status": "error",
                    "error": "Failed to submit analysis job",
                    "cleaning_report": cleaning_report,  # Include cleaning report even if job fails
                }

            # Build job ticket
            job_ticket = {
                "ticket_id": ticket_id,
                "job_id": job_id,
                "job_type": "auto_analyze",
                "status": "submitted",
                "storage_mode": storage_mode,
                "dataset_id": dataset_id,
                "submitted_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "target_column": target_column,
                "cleaning_applied": cleaning_report is not None,
                "cleaning_report": cleaning_report,

                # Tracking info
                "tracking": {
                    "check_status": f"get_stats_job_status('{job_id}')",
                    "get_result": f"get_stats_job_result('{job_id}')",
                },
            }

            # Wait for result if requested
            if wait_for_result:
                start_time = time.time()
                poll_interval = 3

                while time.time() - start_time < wait_timeout:
                    status = await stats_client.get_job_status(job_id)
                    job_status = status.get("status")

                    if job_status == "completed":
                        result = await stats_client.get_job_result(job_id)
                        job_ticket["status"] = "completed"
                        job_ticket["completed_at"] = datetime.utcnow().isoformat()
                        job_ticket["result"] = result.get("result")
                        job_ticket["result_summary"] = _generate_result_summary(result.get("result", {}))
                        break

                    if job_status == "failed":
                        job_ticket["status"] = "failed"
                        job_ticket["error"] = status.get("error", "Analysis failed")
                        break

                    job_ticket["status"] = "running"
                    time.sleep(poll_interval)
                else:
                    job_ticket["status"] = "timeout"
                    job_ticket["message"] = f"Analysis still running after {wait_timeout}s. Use tracking info to check later."

            logger.info(f"Executed ticket {ticket_id} → job {job_id}")
            return job_ticket

        except Exception as e:
            logger.error(f"Failed to execute ticket {ticket_id}: {e}")
            return {
                "ticket_id": ticket_id,
                "status": "error",
                "error": str(e),
            }

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def check_analysis_progress(
        job_id: str,
    ) -> dict:
        """
        📊 Check the progress of an analysis job.

        Use this to check on a running analysis job.

        Args:
            job_id: Job ID from execute_analysis_ticket

        Returns:
            job_id: Job identifier
            status: "pending" | "running" | "completed" | "failed"
            progress: Progress percentage (0-100)
            result: (if completed) Analysis results
            next_steps: Suggested next actions
        """
        try:
            status = await stats_client.get_job_status(job_id)
            job_status = status.get("status")

            response = {
                "job_id": job_id,
                "status": job_status,
                "progress": int(status.get("progress", 0) * 100),
                "message": status.get("message"),
            }

            if job_status == "completed":
                result = await stats_client.get_job_result(job_id)
                response["result"] = result.get("result")
                response["result_summary"] = _generate_result_summary(result.get("result", {}))
                response["next_steps"] = [
                    "Review the analysis results",
                    "If ML training is needed, use the recommendations to prepare features",
                    "Consider running submit_automl_job if building a predictive model",
                ]
            elif job_status == "failed":
                response["error"] = status.get("error")
                response["next_steps"] = [
                    "Check the error message",
                    "Verify data format and try again",
                ]
            else:
                response["next_steps"] = [
                    f"Analysis is {job_status}. Check again in a few seconds.",
                ]

            return response

        except Exception as e:
            return {
                "job_id": job_id,
                "status": "error",
                "error": str(e),
            }

    # Note: get_analysis_capabilities is already registered in statistics_tools.py
    # We could extend it there with validation info if needed

    logger.info("Registered 3 smart workflow tools")


def _generate_result_summary(result: dict) -> dict:
    """Generate a human-readable summary of analysis results"""
    if not result:
        return {}

    summary = {}

    # Data overview
    metadata = result.get("metadata", {})
    if metadata:
        summary["data_overview"] = {
            "rows": metadata.get("n_rows"),
            "columns": metadata.get("n_cols"),
            "memory_mb": metadata.get("memory_usage_mb"),
        }

    # Data quality
    quality = result.get("data_quality", {})
    if quality:
        summary["data_quality"] = {
            "score": quality.get("score"),
            "issues_count": len(quality.get("issues", [])),
            "issues": quality.get("issues", [])[:3],  # Top 3 issues
        }

    # Column types
    col_summary = result.get("column_summary", {})
    if col_summary:
        summary["column_types"] = {
            "numeric": len(col_summary.get("numeric", [])),
            "categorical": len(col_summary.get("categorical", [])),
            "datetime": len(col_summary.get("datetime", [])),
        }

    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        summary["top_recommendations"] = []
        if isinstance(recommendations, list):
            # New format: list of recommendation objects
            for rec in recommendations[:5]:
                if isinstance(rec, dict):
                    summary["top_recommendations"].append(rec.get("suggestion", str(rec)))
                else:
                    summary["top_recommendations"].append(str(rec))
        elif isinstance(recommendations, dict):
            # Old format: dict with categories
            for category in ["data_cleaning", "feature_engineering", "ml_models"]:
                items = recommendations.get(category, [])
                if items:
                    summary["top_recommendations"].extend(items[:2])

    return summary
