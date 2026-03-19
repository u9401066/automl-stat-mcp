"""
Data Validator Module

Provides data quality validation and issue detection for the Smart Workflow.
This acts as a validation layer before analysis or ML training.

Issue Categories:
- CRITICAL: Must be addressed (PII detected)
- HIGH: Should be addressed (>20% missing, invalid types)
- MEDIUM: Recommended to address (outliers, moderate missing)
- LOW: Auto-handled (ID columns, constant columns)
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class IssueSeverity(str, Enum):
    """Issue severity levels"""

    CRITICAL = "critical"  # Must address - blocks processing
    HIGH = "high"  # Should address - may affect results
    MEDIUM = "medium"  # Recommended - quality improvement
    LOW = "low"  # Auto-handled - informational


class IssueType(str, Enum):
    """Types of data quality issues"""

    # Critical
    PII_DETECTED = "pii_detected"  # Entire column is PII (can be deleted/masked)
    PII_EMBEDDED = "pii_embedded"  # PII mixed in other data (needs PHI MCP)

    # High
    HIGH_MISSING_RATIO = "high_missing_ratio"
    INVALID_DATA_TYPE = "invalid_data_type"
    TARGET_HAS_MISSING = "target_has_missing"

    # Medium
    MODERATE_MISSING = "moderate_missing"
    OUTLIERS_DETECTED = "outliers_detected"
    HIGH_CARDINALITY = "high_cardinality"
    CLASS_IMBALANCE = "class_imbalance"
    DUPLICATE_ROWS = "duplicate_rows"

    # Low
    ID_COLUMN = "id_column"
    CONSTANT_COLUMN = "constant_column"
    HIGH_CORRELATION = "high_correlation"


class CleaningAction(str, Enum):
    """Available cleaning actions"""

    # Missing value handling
    DROP_ROWS = "drop_rows"
    DROP_COLUMN = "drop_column"
    FILL_MEAN = "fill_mean"
    FILL_MEDIAN = "fill_median"
    FILL_MODE = "fill_mode"
    FILL_CONSTANT = "fill_constant"

    # Column handling
    EXCLUDE_COLUMN = "exclude_column"
    CONVERT_TYPE = "convert_type"

    # Row handling
    REMOVE_DUPLICATES = "remove_duplicates"
    REMOVE_OUTLIERS = "remove_outliers"

    # PII handling
    MASK_PII = "mask_pii"
    REMOVE_PII_COLUMN = "remove_pii_column"

    # Complex PII - requires external processing
    REQUIRE_PHI_MCP = "require_phi_mcp"  # Needs dedicated PHI MCP to handle
    REJECT_DATA = "reject_data"  # Data too complex, reject entirely

    # No action
    IGNORE = "ignore"
    KEEP_AS_IS = "keep_as_is"


@dataclass
class DataIssue:
    """Represents a single data quality issue"""

    issue_type: IssueType
    severity: IssueSeverity
    column: Optional[str]
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggested_actions: List[CleaningAction] = field(default_factory=list)
    default_action: Optional[CleaningAction] = None
    requires_user_decision: bool = False

    def to_dict(self) -> dict:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "column": self.column,
            "description": self.description,
            "details": self.details,
            "suggested_actions": [a.value for a in self.suggested_actions],
            "default_action": self.default_action.value if self.default_action else None,
            "requires_user_decision": self.requires_user_decision,
        }


@dataclass
class ValidationReport:
    """Complete validation report for a dataset"""

    is_valid: bool
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    issues: List[DataIssue]
    summary: str
    can_proceed: bool  # Can analysis proceed without user intervention?
    requires_user_decisions: List[DataIssue]  # Issues that need user input
    auto_fixable: List[DataIssue]  # Issues that can be auto-fixed

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "can_proceed": self.can_proceed,
            "requires_user_decisions": [i.to_dict() for i in self.requires_user_decisions],
            "auto_fixable": [i.to_dict() for i in self.auto_fixable],
        }


class DataValidator:
    """
    Validates dataset and detects quality issues.

    Usage:
        validator = DataValidator()
        report = validator.validate(df, target_column="price")
    """

    # PII patterns (basic detection)
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "tw_id": r"\b[A-Z][12]\d{8}\b",  # Taiwan ID
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    }

    # Column name patterns suggesting PII
    PII_COLUMN_PATTERNS = [
        r"(?i)^name$",
        r"(?i).*_name$",
        r"(?i)^.*name_.*",  # Name fields
        r"(?i).*fullname.*",
        r"(?i).*first.*name.*",
        r"(?i).*last.*name.*",
        r"(?i)^姓名$",
        r"(?i).*姓名.*",  # Chinese name
        r"(?i).*email.*",
        r"(?i).*e-mail.*",  # Email
        r"(?i).*phone.*",
        r"(?i).*mobile.*",
        r"(?i).*cell.*",  # Phone
        r"(?i).*ssn.*",
        r"(?i).*social.*security.*",  # SSN
        r"(?i).*credit.*card.*",
        r"(?i).*card.*number.*",  # Credit card
        r"(?i).*address.*",
        r"(?i).*addr.*",  # Address
        r"(?i).*passport.*",
        r"(?i).*license.*",  # ID documents
        r"(?i).*身分證.*",
        r"(?i).*電話.*",
        r"(?i).*地址.*",  # Chinese PII
        r"(?i).*password.*",
        r"(?i).*secret.*",
        r"(?i).*token.*",  # Secrets
        r"(?i).*birthday.*",
        r"(?i).*birth.*date.*",
        r"(?i).*dob.*",  # DOB
        r"(?i).*生日.*",
        r"(?i).*出生.*",  # Chinese DOB
    ]

    # ID column patterns
    ID_PATTERNS = [
        r"(?i)^id$",
        r"(?i).*_id$",
        r"(?i)^.*id_.*",
        r"(?i)^index$",
        r"(?i)^row.*",
        r"(?i)^record.*",
        r"(?i)^key$",
        r"(?i).*_key$",
    ]

    def __init__(
        self,
        missing_threshold_high: float = 0.2,
        missing_threshold_medium: float = 0.05,
        outlier_zscore_threshold: float = 3.0,
        cardinality_threshold: float = 0.9,
        correlation_threshold: float = 0.95,
        imbalance_threshold: float = 0.1,
    ):
        self.missing_threshold_high = missing_threshold_high
        self.missing_threshold_medium = missing_threshold_medium
        self.outlier_zscore_threshold = outlier_zscore_threshold
        self.cardinality_threshold = cardinality_threshold
        self.correlation_threshold = correlation_threshold
        self.imbalance_threshold = imbalance_threshold

    def validate(self, df: pd.DataFrame, target_column: Optional[str] = None) -> ValidationReport:
        """
        Validate a DataFrame and return a comprehensive report.

        Args:
            df: DataFrame to validate
            target_column: Optional target column for ML tasks

        Returns:
            ValidationReport with all detected issues
        """
        issues: List[DataIssue] = []

        # Run all checks
        issues.extend(self._check_pii(df))
        issues.extend(self._check_missing_values(df, target_column))
        issues.extend(self._check_id_columns(df))
        issues.extend(self._check_constant_columns(df))
        issues.extend(self._check_data_types(df))
        issues.extend(self._check_outliers(df))
        issues.extend(self._check_duplicates(df))
        issues.extend(self._check_high_cardinality(df))
        issues.extend(self._check_correlations(df))

        if target_column:
            issues.extend(self._check_target_column(df, target_column))

        # Sort by severity
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
        }
        issues.sort(key=lambda x: severity_order[x.severity])

        # Count by severity
        critical = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
        low = sum(1 for i in issues if i.severity == IssueSeverity.LOW)

        # Categorize issues
        requires_user = [i for i in issues if i.requires_user_decision]
        auto_fixable = [i for i in issues if not i.requires_user_decision and i.default_action]

        # Determine if we can proceed
        can_proceed = critical == 0 and len(requires_user) == 0

        # Generate summary
        summary = self._generate_summary(df, issues, critical, high, medium, low)

        return ValidationReport(
            is_valid=len(issues) == 0,
            total_issues=len(issues),
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            issues=issues,
            summary=summary,
            can_proceed=can_proceed,
            requires_user_decisions=requires_user,
            auto_fixable=auto_fixable,
        )

    # Threshold for determining if a column is "entirely PII" vs "embedded PII"
    PII_COLUMN_THRESHOLD = 0.5  # If >50% values match PII pattern, treat as PII column
    PII_EMBEDDED_THRESHOLD = 0.05  # If <5% but some matches, consider embedded PII

    def _check_pii(self, df: pd.DataFrame) -> List[DataIssue]:
        """
        Check for potential PII in data.

        Distinguishes between:
        1. PII_DETECTED: Entire column is clearly PII (>50% matches) - can be deleted/masked
        2. PII_EMBEDDED: PII scattered in other data (<50% matches) - needs PHI MCP
        """
        issues = []
        pii_columns_detected = set()  # Track columns already flagged by name pattern

        for col in df.columns:
            # Check column name patterns (like 'email', 'phone', etc.)
            name_suggests_pii = False
            for pattern in self.PII_COLUMN_PATTERNS:
                if re.match(pattern, col):
                    name_suggests_pii = True
                    pii_columns_detected.add(col)
                    issues.append(
                        DataIssue(
                            issue_type=IssueType.PII_DETECTED,
                            severity=IssueSeverity.CRITICAL,
                            column=col,
                            description=f"欄位 '{col}' 名稱明顯為個資欄位，可刪除或遮罩整欄",
                            details={
                                "detection_method": "column_name_pattern",
                                "handling": "simple",  # Can be handled by delete/mask
                            },
                            suggested_actions=[
                                CleaningAction.REMOVE_PII_COLUMN,
                                CleaningAction.MASK_PII,
                                CleaningAction.KEEP_AS_IS,
                            ],
                            default_action=None,  # User must decide
                            requires_user_decision=True,
                        )
                    )
                    break

            # Skip content check if already flagged by name
            if name_suggests_pii:
                continue

            # Check content for string columns
            if df[col].dtype == "object":
                non_null = df[col].dropna()
                if len(non_null) == 0:
                    continue

                sample = non_null.astype(str)
                sample_size = len(sample)

                for pii_type, pattern in self.PII_PATTERNS.items():
                    matches = sample.str.contains(pattern, regex=True, na=False)
                    match_count = matches.sum()

                    if match_count == 0:
                        continue

                    match_ratio = match_count / sample_size

                    if match_ratio >= self.PII_COLUMN_THRESHOLD:
                        # High ratio: Entire column is PII - can delete/mask column
                        pii_columns_detected.add(col)
                        issues.append(
                            DataIssue(
                                issue_type=IssueType.PII_DETECTED,
                                severity=IssueSeverity.CRITICAL,
                                column=col,
                                description=f"欄位 '{col}' 內容為 {pii_type} ({match_ratio:.0%} 匹配)，可刪除或遮罩整欄",
                                details={
                                    "pii_type": pii_type,
                                    "match_count": int(match_count),
                                    "match_ratio": float(match_ratio),
                                    "detection_method": "content_pattern",
                                    "handling": "simple",  # Can be handled by delete/mask
                                },
                                suggested_actions=[
                                    CleaningAction.REMOVE_PII_COLUMN,
                                    CleaningAction.MASK_PII,
                                    CleaningAction.KEEP_AS_IS,
                                ],
                                default_action=None,
                                requires_user_decision=True,
                            )
                        )
                        break  # One PII type per column is enough

                    elif match_ratio >= self.PII_EMBEDDED_THRESHOLD:
                        # Low ratio: PII embedded in other data - needs PHI MCP
                        issues.append(
                            DataIssue(
                                issue_type=IssueType.PII_EMBEDDED,
                                severity=IssueSeverity.CRITICAL,
                                column=col,
                                description=f"⚠️ 欄位 '{col}' 含有散佈的 {pii_type} ({match_count} 筆)，無法簡單處理，請先使用 PHI MCP 處理",
                                details={
                                    "pii_type": pii_type,
                                    "match_count": int(match_count),
                                    "match_ratio": float(match_ratio),
                                    "detection_method": "content_pattern",
                                    "handling": "complex",  # Needs PHI MCP
                                    "reason": "PII散佈在普通資料中，無法用刪除/遮罩整欄解決",
                                },
                                suggested_actions=[
                                    CleaningAction.REQUIRE_PHI_MCP,
                                    CleaningAction.REJECT_DATA,
                                ],
                                default_action=CleaningAction.REQUIRE_PHI_MCP,
                                requires_user_decision=True,
                            )
                        )
                        break

        return issues

    def _check_missing_values(self, df: pd.DataFrame, target_column: Optional[str]) -> List[DataIssue]:
        """Check for missing values"""
        issues = []

        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_ratio = missing_count / len(df)

            if missing_ratio == 0:
                continue

            if missing_ratio >= self.missing_threshold_high:
                severity = IssueSeverity.HIGH
                requires_decision = True
            elif missing_ratio >= self.missing_threshold_medium:
                severity = IssueSeverity.MEDIUM
                requires_decision = False
            else:
                continue  # Very low missing, skip

            # Determine suggested actions based on column type
            if pd.api.types.is_numeric_dtype(df[col]):
                suggested = [
                    CleaningAction.FILL_MEDIAN,
                    CleaningAction.FILL_MEAN,
                    CleaningAction.DROP_ROWS,
                    CleaningAction.DROP_COLUMN,
                ]
                default = CleaningAction.FILL_MEDIAN
            else:
                suggested = [
                    CleaningAction.FILL_MODE,
                    CleaningAction.FILL_CONSTANT,
                    CleaningAction.DROP_ROWS,
                    CleaningAction.DROP_COLUMN,
                ]
                default = CleaningAction.FILL_MODE

            issue_type = IssueType.HIGH_MISSING_RATIO if severity == IssueSeverity.HIGH else IssueType.MODERATE_MISSING

            issues.append(
                DataIssue(
                    issue_type=issue_type,
                    severity=severity,
                    column=col,
                    description=f"Column '{col}' has {missing_ratio:.1%} missing values ({missing_count} rows)",
                    details={
                        "missing_count": int(missing_count),
                        "missing_ratio": float(missing_ratio),
                        "total_rows": len(df),
                    },
                    suggested_actions=suggested,
                    default_action=default if not requires_decision else None,
                    requires_user_decision=requires_decision,
                )
            )

        return issues

    def _check_id_columns(self, df: pd.DataFrame) -> List[DataIssue]:
        """Detect ID-like columns"""
        issues = []

        for col in df.columns:
            is_id = False
            detection_reason = ""

            # Check column name pattern (high confidence)
            for pattern in self.ID_PATTERNS:
                if re.match(pattern, col):
                    is_id = True
                    detection_reason = "column_name_pattern"
                    break

            # Check if all values are unique AND it's an integer column (medium confidence)
            # Only for datasets with > 10 rows to avoid false positives on small data
            if not is_id and len(df) > 10 and df[col].nunique() == len(df):
                # Only consider integer columns with sequential-like values
                if pd.api.types.is_integer_dtype(df[col]):
                    # Check if values look like sequential IDs (e.g., 1, 2, 3, ...)
                    sorted_vals = df[col].dropna().sort_values()
                    if len(sorted_vals) > 0:
                        min_val, max_val = sorted_vals.iloc[0], sorted_vals.iloc[-1]
                        if max_val - min_val == len(sorted_vals) - 1:
                            is_id = True
                            detection_reason = "sequential_integer"

            if is_id:
                issues.append(
                    DataIssue(
                        issue_type=IssueType.ID_COLUMN,
                        severity=IssueSeverity.LOW,
                        column=col,
                        description=f"Column '{col}' appears to be an ID column (will be excluded from modeling)",
                        details={
                            "unique_values": int(df[col].nunique()),
                            "detection_reason": detection_reason,
                        },
                        suggested_actions=[
                            CleaningAction.EXCLUDE_COLUMN,
                            CleaningAction.KEEP_AS_IS,
                        ],
                        default_action=CleaningAction.EXCLUDE_COLUMN,
                        requires_user_decision=False,
                    )
                )

        return issues

    def _check_constant_columns(self, df: pd.DataFrame) -> List[DataIssue]:
        """Detect constant columns (single value)"""
        issues = []

        for col in df.columns:
            if df[col].nunique(dropna=True) <= 1:
                issues.append(
                    DataIssue(
                        issue_type=IssueType.CONSTANT_COLUMN,
                        severity=IssueSeverity.LOW,
                        column=col,
                        description=f"Column '{col}' has only one unique value (will be excluded)",
                        details={"unique_value": str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else None},
                        suggested_actions=[
                            CleaningAction.EXCLUDE_COLUMN,
                            CleaningAction.KEEP_AS_IS,
                        ],
                        default_action=CleaningAction.EXCLUDE_COLUMN,
                        requires_user_decision=False,
                    )
                )

        return issues

    def _check_data_types(self, df: pd.DataFrame) -> List[DataIssue]:
        """Check for potential data type issues"""
        issues = []

        for col in df.columns:
            if df[col].dtype == "object":
                # Try to detect if it should be numeric
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    # Check if values look numeric
                    numeric_pattern = r"^-?\d+\.?\d*$"
                    is_numeric_like = non_null.astype(str).str.match(numeric_pattern).mean()

                    if is_numeric_like > 0.8:  # 80% look numeric
                        issues.append(
                            DataIssue(
                                issue_type=IssueType.INVALID_DATA_TYPE,
                                severity=IssueSeverity.HIGH,
                                column=col,
                                description=f"Column '{col}' appears to contain numeric data but is stored as text",
                                details={
                                    "current_type": "object",
                                    "suggested_type": "numeric",
                                    "numeric_like_ratio": float(is_numeric_like),
                                },
                                suggested_actions=[
                                    CleaningAction.CONVERT_TYPE,
                                    CleaningAction.KEEP_AS_IS,
                                ],
                                default_action=CleaningAction.CONVERT_TYPE,
                                requires_user_decision=False,
                            )
                        )

        return issues

    def _check_outliers(self, df: pd.DataFrame) -> List[DataIssue]:
        """Detect outliers in numeric columns using IQR method (more robust than z-score)"""
        issues = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            values = df[col].dropna()
            if len(values) < 10:
                continue

            # IQR method (more robust to outliers than z-score)
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (values < lower_bound) | (values > upper_bound)
            outlier_count = outlier_mask.sum()
            outlier_ratio = outlier_count / len(values)

            if outlier_count > 0 and outlier_ratio > 0.01:  # More than 1% outliers
                issues.append(
                    DataIssue(
                        issue_type=IssueType.OUTLIERS_DETECTED,
                        severity=IssueSeverity.MEDIUM,
                        column=col,
                        description=f"Column '{col}' has {outlier_count} potential outliers ({outlier_ratio:.1%})",
                        details={
                            "outlier_count": int(outlier_count),
                            "outlier_ratio": float(outlier_ratio),
                            "method": "IQR",
                            "q1": float(q1),
                            "q3": float(q3),
                            "iqr": float(iqr),
                            "lower_bound": float(lower_bound),
                            "upper_bound": float(upper_bound),
                        },
                        suggested_actions=[
                            CleaningAction.KEEP_AS_IS,
                            CleaningAction.REMOVE_OUTLIERS,
                        ],
                        default_action=CleaningAction.KEEP_AS_IS,
                        requires_user_decision=False,
                    )
                )

        return issues

    def _check_duplicates(self, df: pd.DataFrame) -> List[DataIssue]:
        """Check for duplicate rows"""
        dup_count = df.duplicated().sum()

        if dup_count > 0:
            return [
                DataIssue(
                    issue_type=IssueType.DUPLICATE_ROWS,
                    severity=IssueSeverity.MEDIUM,
                    column=None,
                    description=f"Dataset has {dup_count} duplicate rows ({dup_count / len(df):.1%})",
                    details={
                        "duplicate_count": int(dup_count),
                        "duplicate_ratio": float(dup_count / len(df)),
                    },
                    suggested_actions=[
                        CleaningAction.REMOVE_DUPLICATES,
                        CleaningAction.KEEP_AS_IS,
                    ],
                    default_action=CleaningAction.REMOVE_DUPLICATES,
                    requires_user_decision=False,
                )
            ]

        return []

    def _check_high_cardinality(self, df: pd.DataFrame) -> List[DataIssue]:
        """Check for high cardinality categorical columns"""
        issues = []

        for col in df.select_dtypes(include=["object"]).columns:
            cardinality_ratio = df[col].nunique() / len(df)

            if cardinality_ratio > self.cardinality_threshold:
                issues.append(
                    DataIssue(
                        issue_type=IssueType.HIGH_CARDINALITY,
                        severity=IssueSeverity.MEDIUM,
                        column=col,
                        description=f"Column '{col}' has very high cardinality ({df[col].nunique()} unique values)",
                        details={
                            "unique_count": int(df[col].nunique()),
                            "cardinality_ratio": float(cardinality_ratio),
                        },
                        suggested_actions=[
                            CleaningAction.EXCLUDE_COLUMN,
                            CleaningAction.KEEP_AS_IS,
                        ],
                        default_action=CleaningAction.KEEP_AS_IS,
                        requires_user_decision=False,
                    )
                )

        return issues

    def _check_correlations(self, df: pd.DataFrame) -> List[DataIssue]:
        """Check for highly correlated features"""
        issues: List[DataIssue] = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return issues

        try:
            corr_matrix = df[numeric_cols].corr().abs()

            # Find high correlations (excluding self-correlation)
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    if corr_matrix.iloc[i, j] > self.correlation_threshold:
                        high_corr_pairs.append(
                            {
                                "col1": corr_matrix.columns[i],
                                "col2": corr_matrix.columns[j],
                                "correlation": float(corr_matrix.iloc[i, j]),
                            }
                        )

            if high_corr_pairs:
                issues.append(
                    DataIssue(
                        issue_type=IssueType.HIGH_CORRELATION,
                        severity=IssueSeverity.LOW,
                        column=None,
                        description=f"Found {len(high_corr_pairs)} pairs of highly correlated features (r > {self.correlation_threshold})",
                        details={"correlated_pairs": high_corr_pairs},
                        suggested_actions=[
                            CleaningAction.KEEP_AS_IS,
                            CleaningAction.EXCLUDE_COLUMN,
                        ],
                        default_action=CleaningAction.KEEP_AS_IS,
                        requires_user_decision=False,
                    )
                )
        except Exception as e:
            logger.warning(f"Could not compute correlations: {e}")

        return issues

    def _check_target_column(self, df: pd.DataFrame, target_column: str) -> List[DataIssue]:
        """Check target column specific issues"""
        issues: List[DataIssue] = []

        if target_column not in df.columns:
            return issues

        target = df[target_column]

        # Check for missing values in target
        missing = target.isna().sum()
        if missing > 0:
            issues.append(
                DataIssue(
                    issue_type=IssueType.TARGET_HAS_MISSING,
                    severity=IssueSeverity.HIGH,
                    column=target_column,
                    description=f"Target column '{target_column}' has {missing} missing values",
                    details={
                        "missing_count": int(missing),
                        "missing_ratio": float(missing / len(df)),
                    },
                    suggested_actions=[
                        CleaningAction.DROP_ROWS,
                    ],
                    default_action=None,
                    requires_user_decision=True,
                )
            )

        # Check for class imbalance (classification)
        if target.dtype == "object" or target.nunique() < 20:
            value_counts = target.value_counts(normalize=True)
            min_class_ratio = value_counts.min()

            if min_class_ratio < self.imbalance_threshold:
                issues.append(
                    DataIssue(
                        issue_type=IssueType.CLASS_IMBALANCE,
                        severity=IssueSeverity.MEDIUM,
                        column=target_column,
                        description=f"Target column has class imbalance (minority class: {min_class_ratio:.1%})",
                        details={
                            "class_distribution": value_counts.to_dict(),
                            "minority_class_ratio": float(min_class_ratio),
                        },
                        suggested_actions=[
                            CleaningAction.KEEP_AS_IS,
                        ],
                        default_action=CleaningAction.KEEP_AS_IS,
                        requires_user_decision=False,
                    )
                )

        return issues

    def _generate_summary(
        self,
        df: pd.DataFrame,
        issues: List[DataIssue],
        critical: int,
        high: int,
        medium: int,
        low: int,
    ) -> str:
        """Generate human-readable summary"""
        lines = [f"Dataset: {len(df)} rows × {len(df.columns)} columns"]

        if len(issues) == 0:
            lines.append("✅ No data quality issues detected!")
        else:
            lines.append(f"Found {len(issues)} issues:")
            if critical > 0:
                lines.append(f"  🔴 {critical} critical (requires attention)")
            if high > 0:
                lines.append(f"  🟠 {high} high priority")
            if medium > 0:
                lines.append(f"  🟡 {medium} medium priority")
            if low > 0:
                lines.append(f"  🟢 {low} low priority (auto-handled)")

        return "\n".join(lines)


# Singleton instance
_validator = None


def get_validator() -> DataValidator:
    """Get or create validator instance"""
    global _validator
    if _validator is None:
        _validator = DataValidator()
    return _validator


def validate_dataframe(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
) -> ValidationReport:
    """Convenience function to validate a DataFrame"""
    return get_validator().validate(df, target_column)
