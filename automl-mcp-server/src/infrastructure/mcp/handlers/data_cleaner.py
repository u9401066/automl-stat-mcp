"""
Data Cleaner Module

Applies cleaning actions to a DataFrame based on user decisions or defaults.
Works with the DataValidator to fix detected issues.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .data_validator import (
    CleaningAction,
    DataIssue,
    IssueType,
    ValidationReport,
)

logger = logging.getLogger(__name__)

DecisionValue = CleaningAction | str
DecisionMap = Dict[str, DecisionValue]


class CleaningResult:
    """Result of a cleaning operation"""

    def __init__(
        self,
        success: bool,
        df: pd.DataFrame,
        actions_applied: List[Dict[str, Any]],
        rows_before: int,
        rows_after: int,
        columns_before: int,
        columns_after: int,
        warnings: List[str],
        error: Optional[str] = None,
        requires_phi_mcp: bool = False,
        phi_columns: Optional[List[str]] = None,
    ):
        self.success = success
        self.df = df
        self.actions_applied = actions_applied
        self.rows_before = rows_before
        self.rows_after = rows_after
        self.columns_before = columns_before
        self.columns_after = columns_after
        self.warnings = warnings
        self.error = error
        self.requires_phi_mcp = requires_phi_mcp
        self.phi_columns = phi_columns or []

    def to_dict(self) -> dict:
        result = {
            "success": self.success,
            "actions_applied": self.actions_applied,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "rows_removed": self.rows_before - self.rows_after,
            "columns_before": self.columns_before,
            "columns_after": self.columns_after,
            "columns_removed": self.columns_before - self.columns_after,
            "warnings": self.warnings,
        }
        if self.error:
            result["error"] = self.error
        if self.requires_phi_mcp:
            result["requires_phi_mcp"] = True
            result["phi_columns"] = self.phi_columns
            result["message"] = "請先使用 PHI MCP 處理含有散佈個資的欄位"
        return result


class DataCleaner:
    """
    Cleans a DataFrame based on validation report and user decisions.

    Usage:
        cleaner = DataCleaner()
        result = cleaner.clean(df, validation_report, user_decisions)
    """

    def clean(
        self,
        df: pd.DataFrame,
        validation_report: ValidationReport,
        user_decisions: Optional[DecisionMap] = None,
    ) -> CleaningResult:
        """
        Clean the DataFrame based on issues and decisions.

        Args:
            df: DataFrame to clean
            validation_report: Report from DataValidator
            user_decisions: Dict mapping issue column/type to chosen action
                           e.g., {"email_column": "remove_pii_column", "age": "fill_median"}

        Returns:
            CleaningResult with cleaned DataFrame and summary
        """
        user_decisions = user_decisions or {}

        rows_before = len(df)
        columns_before = len(df.columns)

        # First pass: Check for PII_EMBEDDED issues that need PHI MCP
        phi_columns: List[str] = []
        for issue in validation_report.issues:
            if issue.issue_type == IssueType.PII_EMBEDDED:
                # Check if user provided a decision for this column
                action = self._get_action(issue, user_decisions)

                # If no decision or decision is REQUIRE_PHI_MCP, we need to stop
                if action is None or action == CleaningAction.REQUIRE_PHI_MCP:
                    if issue.column is not None:
                        phi_columns.append(issue.column)
                elif action == CleaningAction.REJECT_DATA:
                    # User explicitly rejected
                    return CleaningResult(
                        success=False,
                        df=df,
                        actions_applied=[],
                        rows_before=rows_before,
                        rows_after=rows_before,
                        columns_before=columns_before,
                        columns_after=columns_before,
                        warnings=[],
                        error=f"❌ 資料被拒絕: 欄位 '{issue.column}' 含有複雜的 PII 無法處理",
                        requires_phi_mcp=False,
                        phi_columns=[],
                    )

        # If there are embedded PII columns without proper handling, return error
        if phi_columns:
            return CleaningResult(
                success=False,
                df=df,
                actions_applied=[],
                rows_before=rows_before,
                rows_after=rows_before,
                columns_before=columns_before,
                columns_after=columns_before,
                warnings=[],
                error="⚠️ 發現散佈的 PII 無法簡單處理，請先使用 PHI MCP 處理",
                requires_phi_mcp=True,
                phi_columns=phi_columns,
            )

        # Work on a copy
        df_clean = df.copy()

        actions_applied: List[Dict[str, Any]] = []
        warnings: List[str] = []
        columns_to_exclude: set[str] = set()

        # Process each issue
        for issue in validation_report.issues:
            # Determine action: user decision > default > ignore
            action = self._get_action(issue, user_decisions)

            if action is None or action == CleaningAction.IGNORE:
                continue

            if action == CleaningAction.KEEP_AS_IS:
                continue

            # Apply the action
            try:
                df_clean, applied, warning = self._apply_action(df_clean, issue, action, columns_to_exclude)

                if applied:
                    actions_applied.append(
                        {
                            "issue_type": issue.issue_type.value,
                            "column": issue.column,
                            "action": action.value,
                            "description": issue.description,
                        }
                    )

                if warning:
                    warnings.append(warning)

            except ValueError as e:
                # REQUIRE_PHI_MCP or REJECT_DATA raised
                return CleaningResult(
                    success=False,
                    df=df,
                    actions_applied=actions_applied,
                    rows_before=rows_before,
                    rows_after=rows_before,
                    columns_before=columns_before,
                    columns_after=columns_before,
                    warnings=warnings,
                    error=str(e),
                    requires_phi_mcp="PHI MCP" in str(e),
                    phi_columns=[issue.column] if issue.column else [],
                )
            except Exception as e:
                warnings.append(f"Failed to apply {action.value} to {issue.column}: {str(e)}")
                logger.warning(f"Cleaning action failed: {e}")

        # Remove excluded columns
        if columns_to_exclude:
            df_clean = df_clean.drop(columns=list(columns_to_exclude), errors="ignore")
            for col in columns_to_exclude:
                actions_applied.append(
                    {
                        "issue_type": "column_excluded",
                        "column": col,
                        "action": "exclude_column",
                        "description": f"Column '{col}' excluded from analysis",
                    }
                )

        return CleaningResult(
            success=True,
            df=df_clean,
            actions_applied=actions_applied,
            rows_before=rows_before,
            rows_after=len(df_clean),
            columns_before=columns_before,
            columns_after=len(df_clean.columns),
            warnings=warnings,
        )

    def _get_action(
        self,
        issue: DataIssue,
        user_decisions: DecisionMap,
    ) -> Optional[CleaningAction]:
        """Determine which action to take for an issue"""

        # Check user decisions by column name
        if issue.column and issue.column in user_decisions:
            action = self._parse_action(user_decisions[issue.column])

            # PII-specific actions should only apply to PII issues
            pii_actions = {CleaningAction.MASK_PII, CleaningAction.REMOVE_PII_COLUMN}
            pii_issue_types = {IssueType.PII_DETECTED, IssueType.PII_EMBEDDED}

            if action in pii_actions and issue.issue_type not in pii_issue_types:
                # User's PII action doesn't apply to non-PII issues
                # Fall through to check default action
                pass
            else:
                return action

        # Check user decisions by issue type
        if issue.issue_type.value in user_decisions:
            action_str = user_decisions[issue.issue_type.value]
            return self._parse_action(action_str)

        # Use default action if issue doesn't require user decision
        if not issue.requires_user_decision and issue.default_action:
            return issue.default_action

        # No action (requires user decision but not provided)
        return None

    def _parse_action(self, action: Any) -> CleaningAction:
        """Parse action from string or enum"""
        if isinstance(action, CleaningAction):
            return action
        if isinstance(action, str):
            try:
                return CleaningAction(action)
            except ValueError:
                return CleaningAction.IGNORE
        return CleaningAction.IGNORE

    def _apply_action(
        self,
        df: pd.DataFrame,
        issue: DataIssue,
        action: CleaningAction,
        columns_to_exclude: set,
    ) -> Tuple[pd.DataFrame, bool, Optional[str]]:
        """
        Apply a single cleaning action.

        Returns:
            Tuple of (modified df, was_applied, warning_message)
        """
        col = issue.column
        warning = None

        # Reject data entirely - raise exception to abort
        if action == CleaningAction.REJECT_DATA:
            raise ValueError(
                f"❌ 資料被拒絕: 欄位 '{col}' 含有複雜的 PII/PHI 資料無法處理。請先使用 PHI MCP 處理後再重試。"
            )

        # Require PHI MCP - this is a blocking action
        if action == CleaningAction.REQUIRE_PHI_MCP:
            raise ValueError(
                f"⚠️ 欄位 '{col}' 含有散佈的 PII ({issue.details.get('pii_type', 'unknown')})，"
                f"無法用簡單的刪除/遮罩處理。請先使用 PHI MCP 處理此欄位後再繼續分析。"
            )

        # Column exclusion actions
        if action in [CleaningAction.EXCLUDE_COLUMN, CleaningAction.DROP_COLUMN, CleaningAction.REMOVE_PII_COLUMN]:
            if col and col in df.columns:
                columns_to_exclude.add(col)
                return df, True, None

        # Row-based actions
        if action == CleaningAction.DROP_ROWS:
            if col and col in df.columns:
                before = len(df)
                df = df.dropna(subset=[col])
                after = len(df)
                if before - after > 0:
                    return df, True, f"Dropped {before - after} rows with missing {col}"

        if action == CleaningAction.REMOVE_DUPLICATES:
            before = len(df)
            df = df.drop_duplicates()
            after = len(df)
            if before - after > 0:
                return df, True, f"Removed {before - after} duplicate rows"

        if action == CleaningAction.REMOVE_OUTLIERS:
            if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    before = len(df)
                    df = df[np.abs((df[col] - mean) / std) <= 3]
                    after = len(df)
                    if before - after > 0:
                        return df, True, f"Removed {before - after} outlier rows from {col}"

        # Fill missing values
        if action == CleaningAction.FILL_MEAN:
            if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                fill_value = df[col].mean()
                df[col] = df[col].fillna(fill_value)
                return df, True, None

        if action == CleaningAction.FILL_MEDIAN:
            if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                fill_value = df[col].median()
                df[col] = df[col].fillna(fill_value)
                return df, True, None

        if action == CleaningAction.FILL_MODE:
            if col and col in df.columns:
                mode_values = df[col].mode()
                if len(mode_values) > 0:
                    df[col] = df[col].fillna(mode_values[0])
                    return df, True, None

        if action == CleaningAction.FILL_CONSTANT:
            if col and col in df.columns:
                fill_value = issue.details.get("fill_value", "MISSING")
                df[col] = df[col].fillna(fill_value)
                return df, True, None

        # Type conversion
        if action == CleaningAction.CONVERT_TYPE:
            if col and col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    return df, True, None
                except Exception as e:
                    warning = f"Could not convert {col} to numeric: {e}"

        # PII masking
        if action == CleaningAction.MASK_PII:
            if col and col in df.columns:
                df[col] = df[col].apply(lambda x: "***MASKED***" if pd.notna(x) else x)
                return df, True, None

        return df, False, warning

    def get_default_actions(
        self,
        validation_report: ValidationReport,
    ) -> Dict[str, str]:
        """
        Get default cleaning actions for all issues in the validation report.

        Returns a dict mapping column/issue_type to default action string.
        This can be passed to clean() or modified by user before cleaning.
        """
        defaults = {}

        for issue in validation_report.issues:
            if issue.default_action:
                key = issue.column if issue.column else issue.issue_type.value
                defaults[key] = issue.default_action.value

        return defaults

    def generate_cleaning_report(
        self,
        original_df: Optional[pd.DataFrame],
        cleaned_df: pd.DataFrame,
        validation_report: ValidationReport,
        decisions: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Generate a human-readable cleaning report.

        Args:
            original_df: Original DataFrame (can be None)
            cleaned_df: Cleaned DataFrame
            validation_report: ValidationReport with issues
            decisions: Actions that were applied

        Returns:
            Report dict with summary and details
        """
        report = {
            "issues_found": validation_report.total_issues,
            "issues_addressed": len(decisions),
            "actions_applied": decisions,
            "summary": {
                "critical_addressed": sum(
                    1
                    for i in validation_report.issues
                    if i.severity.value == "critical" and (i.column in decisions or i.issue_type.value in decisions)
                ),
                "high_addressed": sum(
                    1
                    for i in validation_report.issues
                    if i.severity.value == "high" and (i.column in decisions or i.issue_type.value in decisions)
                ),
            },
        }
        return report

    def apply_auto_fixes(
        self,
        df: pd.DataFrame,
        validation_report: ValidationReport,
    ) -> CleaningResult:
        """
        Apply only auto-fixable issues (no user decision required).

        This is useful for quick processing when user doesn't want to
        make decisions about minor issues.
        """
        # Only process auto-fixable issues
        auto_decisions = {}

        for issue in validation_report.auto_fixable:
            if issue.default_action:
                key = issue.column or issue.issue_type.value
                auto_decisions[key] = issue.default_action

        return self.clean(df, validation_report, auto_decisions)


# Singleton instance
_cleaner = None


def get_cleaner() -> DataCleaner:
    """Get or create cleaner instance"""
    global _cleaner
    if _cleaner is None:
        _cleaner = DataCleaner()
    return _cleaner


def clean_dataframe(
    df: pd.DataFrame,
    validation_report: ValidationReport,
    user_decisions: Optional[DecisionMap] = None,
) -> CleaningResult:
    """Convenience function to clean a DataFrame"""
    return get_cleaner().clean(df, validation_report, user_decisions)


def auto_clean_dataframe(
    df: pd.DataFrame,
    validation_report: ValidationReport,
) -> CleaningResult:
    """Convenience function for auto-cleaning only"""
    return get_cleaner().apply_auto_fixes(df, validation_report)
