"""
Data Quality Analyzer - 資料品質分析模組

提供統一的資料品質檢測和建議功能：
- 全 NaN 欄偵測
- 常數欄偵測
- 高基數 ID 欄偵測
- 偏態資料偵測
- 極端值偵測
- Transform 建議
- 分析可行性評估
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class IssueSeverity(str, Enum):
    """品質問題嚴重程度"""

    CRITICAL = "critical"  # 阻斷分析
    WARNING = "warning"  # 需要注意
    INFO = "info"  # 建議改進


class IssueType(str, Enum):
    """品質問題類型"""

    ALL_NAN = "ALL_NAN"
    CONSTANT = "CONSTANT"
    HIGH_CARDINALITY_ID = "HIGH_CARDINALITY_ID"
    SKEWED = "SKEWED"
    OUTLIERS = "OUTLIERS"
    HIGH_MISSING = "HIGH_MISSING"
    NEGATIVE_VALUES = "NEGATIVE_VALUES"


class TransformType(str, Enum):
    """Transform 類型"""

    LOG = "log"
    LOG1P = "log1p"
    SQRT = "sqrt"
    ZSCORE = "zscore"
    NONE = "none"


@dataclass
class QualityWarning:
    """品質警告"""

    column: str
    issue: str
    severity: str
    recommendation: str
    impact: str
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TransformSuggestion:
    """Transform 建議"""

    column: str
    suggested_transform: str
    reason: str
    before_stats: Dict[str, float]
    after_preview: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisReadiness:
    """分析可行性評估"""

    ready: bool
    blocking_issues: List[str]
    warnings: List[str]
    recommended_actions: List[str]
    usable_columns: List[str]
    problematic_columns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataQualityReport:
    """資料品質報告"""

    warnings: List[QualityWarning]
    transform_suggestions: List[TransformSuggestion]
    analysis_readiness: AnalysisReadiness

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_warnings": [w.to_dict() for w in self.warnings],
            "transform_suggestions": [t.to_dict() for t in self.transform_suggestions],
            "analysis_readiness": self.analysis_readiness.to_dict(),
        }


class DataQualityAnalyzer:
    """
    資料品質分析器

    提供統一的資料品質檢測和建議功能。

    Usage:
        analyzer = DataQualityAnalyzer()
        report = analyzer.analyze(df)
        print(report.to_dict())
    """

    # 閾值設定
    SKEW_THRESHOLD = 1.0  # mean/median 比率閾值
    HIGH_CARDINALITY_THRESHOLD = 0.9  # unique/rows 比率閾值
    OUTLIER_IQR_MULTIPLIER = 1.5  # IQR 乘數
    HIGH_MISSING_THRESHOLD = 0.5  # 缺失值比率閾值
    MIN_ROWS_FOR_ID_DETECTION = 5  # ID 欄偵測最小行數

    def __init__(
        self,
        skew_threshold: float = 1.0,
        high_cardinality_threshold: float = 0.9,
        outlier_iqr_multiplier: float = 1.5,
        high_missing_threshold: float = 0.5,
    ):
        """
        初始化分析器

        Args:
            skew_threshold: 偏態閾值 (mean/median 比率)
            high_cardinality_threshold: 高基數閾值 (unique/rows 比率)
            outlier_iqr_multiplier: 極端值 IQR 乘數
            high_missing_threshold: 高缺失值閾值
        """
        self.SKEW_THRESHOLD = skew_threshold
        self.HIGH_CARDINALITY_THRESHOLD = high_cardinality_threshold
        self.OUTLIER_IQR_MULTIPLIER = outlier_iqr_multiplier
        self.HIGH_MISSING_THRESHOLD = high_missing_threshold

    def analyze(self, df: pd.DataFrame) -> DataQualityReport:
        """
        完整資料品質分析

        Args:
            df: 要分析的 DataFrame

        Returns:
            DataQualityReport: 品質報告
        """
        warnings: List[QualityWarning] = []
        transform_suggestions: List[TransformSuggestion] = []
        blocking_issues: List[str] = []
        warning_issues: List[str] = []
        usable_columns: List[str] = []
        problematic_columns: List[str] = []

        n_rows = len(df)

        for col in df.columns:
            col_warnings = []
            is_usable = True

            # 1. 檢查全 NaN
            if df[col].isna().all():
                warning = QualityWarning(
                    column=col,
                    issue=IssueType.ALL_NAN.value,
                    severity=IssueSeverity.CRITICAL.value,
                    recommendation="移除此欄或填補缺失值",
                    impact="此欄不會被納入任何統計分析",
                    stats={"null_count": int(n_rows), "null_pct": 100.0},
                )
                col_warnings.append(warning)
                blocking_issues.append(f"{IssueType.ALL_NAN.value}:{col}")
                is_usable = False
                problematic_columns.append(col)
                warnings.append(warning)
                continue

            # 2. 檢查高缺失值
            null_count = df[col].isna().sum()
            null_pct = null_count / n_rows
            if null_pct >= self.HIGH_MISSING_THRESHOLD:
                warning = QualityWarning(
                    column=col,
                    issue=IssueType.HIGH_MISSING.value,
                    severity=IssueSeverity.WARNING.value,
                    recommendation="考慮填補缺失值或排除此欄",
                    impact=f"有 {null_pct:.1%} 的資料缺失，可能影響分析結果",
                    stats={"null_count": int(null_count), "null_pct": round(null_pct * 100, 1)},
                )
                col_warnings.append(warning)
                warning_issues.append(f"{IssueType.HIGH_MISSING.value}:{col}")
                warnings.append(warning)

            # 3. 檢查常數欄
            n_unique = df[col].nunique()
            if n_unique == 1:
                warning = QualityWarning(
                    column=col,
                    issue=IssueType.CONSTANT.value,
                    severity=IssueSeverity.WARNING.value,
                    recommendation="移除此欄，無分析價值",
                    impact="常數欄的相關性為 NaN，無法用於迴歸或分組",
                    stats={"unique": 1, "value": str(df[col].dropna().iloc[0]) if len(df[col].dropna()) > 0 else None},
                )
                col_warnings.append(warning)
                warning_issues.append(f"{IssueType.CONSTANT.value}:{col}")
                is_usable = False
                problematic_columns.append(col)
                warnings.append(warning)
                continue

            # 4. 檢查高基數 ID 欄
            cardinality_ratio = n_unique / n_rows if n_rows > 0 else 0
            if cardinality_ratio >= self.HIGH_CARDINALITY_THRESHOLD and n_rows >= self.MIN_ROWS_FOR_ID_DETECTION:
                # 檢查是否像 ID 欄位（字串類型或名稱含 id/uuid/mrn 等）
                is_likely_id = df[col].dtype == "object" or any(
                    pattern in col.lower() for pattern in ["id", "uuid", "mrn", "key", "code", "no.", "num"]
                )
                if is_likely_id:
                    warning = QualityWarning(
                        column=col,
                        issue=IssueType.HIGH_CARDINALITY_ID.value,
                        severity=IssueSeverity.WARNING.value,
                        recommendation="排除於統計分析外",
                        impact="不適合作為分類或分組變數",
                        stats={"unique": int(n_unique), "cardinality_ratio": round(float(cardinality_ratio), 3)},
                    )
                    col_warnings.append(warning)
                    warning_issues.append(f"{IssueType.HIGH_CARDINALITY_ID.value}:{col}")
                    is_usable = False
                    problematic_columns.append(col)
                    warnings.append(warning)
                    continue

            # 5. 檢查數值欄位的偏態和極端值
            if pd.api.types.is_numeric_dtype(df[col]) and df[col].dtype != "bool":
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    mean = non_null.mean()
                    median = non_null.median()
                    std = non_null.std()

                    # 偏態檢測
                    if median > 0 and not np.isnan(mean) and not np.isnan(median):
                        skew_ratio = abs(mean - median) / median
                        if skew_ratio > self.SKEW_THRESHOLD:
                            warning = QualityWarning(
                                column=col,
                                issue=IssueType.SKEWED.value,
                                severity=IssueSeverity.INFO.value,
                                recommendation="考慮 log transform 或使用非參數方法",
                                impact="參數統計方法（如 t-test）可能不準確",
                                stats={
                                    "mean": round(float(mean), 4),
                                    "median": round(float(median), 4),
                                    "skew_ratio": round(float(skew_ratio), 2),
                                },
                            )
                            col_warnings.append(warning)
                            warning_issues.append(f"{IssueType.SKEWED.value}:{col}")
                            warnings.append(warning)

                            # 建議 Transform
                            transform = self._suggest_transform(non_null, col, mean, median, skew_ratio)
                            if transform:
                                transform_suggestions.append(transform)

                    # 極端值檢測
                    if std > 0:
                        q1 = non_null.quantile(0.25)
                        q3 = non_null.quantile(0.75)
                        iqr = q3 - q1
                        lower_bound = q1 - self.OUTLIER_IQR_MULTIPLIER * iqr
                        upper_bound = q3 + self.OUTLIER_IQR_MULTIPLIER * iqr

                        outliers = non_null[(non_null < lower_bound) | (non_null > upper_bound)]
                        if len(outliers) > 0:
                            outlier_pct = len(outliers) / len(non_null) * 100
                            if outlier_pct >= 5:  # 超過 5% 才警告
                                warning = QualityWarning(
                                    column=col,
                                    issue=IssueType.OUTLIERS.value,
                                    severity=IssueSeverity.INFO.value,
                                    recommendation="檢查極端值是否為真實資料或錯誤",
                                    impact="極端值可能影響平均數和迴歸係數",
                                    stats={
                                        "outlier_count": int(len(outliers)),
                                        "outlier_pct": round(float(outlier_pct), 1),
                                        "lower_bound": round(float(lower_bound), 4),
                                        "upper_bound": round(float(upper_bound), 4),
                                        "min": round(float(non_null.min()), 4),
                                        "max": round(float(non_null.max()), 4),
                                    },
                                )
                                col_warnings.append(warning)
                                warning_issues.append(f"{IssueType.OUTLIERS.value}:{col}")
                                warnings.append(warning)

                    # 檢查負值（某些分析需要正值）
                    if (non_null < 0).any():
                        neg_count = (non_null < 0).sum()
                        neg_count / len(non_null) * 100
                        # 只記錄，不作為警告（某些資料負值是正常的）

            # 記錄可用欄位
            if is_usable and col not in problematic_columns:
                usable_columns.append(col)

        # 生成建議動作
        recommended_actions = self._generate_recommendations(warnings)

        # 評估分析可行性
        # 如果所有欄位都有問題，則不適合分析
        ready = len(blocking_issues) == 0 and len(usable_columns) > 0

        analysis_readiness = AnalysisReadiness(
            ready=ready,
            blocking_issues=blocking_issues,
            warnings=warning_issues,
            recommended_actions=recommended_actions,
            usable_columns=usable_columns,
            problematic_columns=list(set(problematic_columns)),
        )

        return DataQualityReport(
            warnings=warnings, transform_suggestions=transform_suggestions, analysis_readiness=analysis_readiness
        )

    def _suggest_transform(
        self, data: pd.Series, col: str, mean: float, median: float, skew_ratio: float
    ) -> Optional[TransformSuggestion]:
        """建議適當的 Transform"""

        # 檢查是否可以使用 log（所有值必須 > 0）
        if (data > 0).all():
            log_data = np.log(data)
            return TransformSuggestion(
                column=col,
                suggested_transform=TransformType.LOG.value,
                reason=f"嚴重正偏態 (skew_ratio={skew_ratio:.2f})，所有值為正",
                before_stats={"mean": round(float(mean), 4), "median": round(float(median), 4)},
                after_preview={"mean": round(float(log_data.mean()), 4), "median": round(float(log_data.median()), 4)},
            )

        # 檢查是否可以使用 log1p（所有值必須 >= 0）
        if (data >= 0).all():
            log1p_data = np.log1p(data)
            return TransformSuggestion(
                column=col,
                suggested_transform=TransformType.LOG1P.value,
                reason=f"嚴重正偏態 (skew_ratio={skew_ratio:.2f})，含零值",
                before_stats={"mean": round(float(mean), 4), "median": round(float(median), 4)},
                after_preview={
                    "mean": round(float(log1p_data.mean()), 4),
                    "median": round(float(log1p_data.median()), 4),
                },
            )

        # 含負值，建議 zscore
        return TransformSuggestion(
            column=col,
            suggested_transform=TransformType.ZSCORE.value,
            reason=f"偏態 (skew_ratio={skew_ratio:.2f})，含負值，建議標準化",
            before_stats={"mean": round(float(mean), 4), "median": round(float(median), 4)},
            after_preview={"mean": 0.0, "std": 1.0},
        )

    def _generate_recommendations(self, warnings: List[QualityWarning]) -> List[str]:
        """生成建議動作列表"""
        recommendations = []

        for w in warnings:
            if w.severity == IssueSeverity.CRITICAL.value:
                if w.issue == IssueType.ALL_NAN.value:
                    recommendations.append(f"移除 `{w.column}` 欄位（全部為缺失值）")
            elif w.issue == IssueType.CONSTANT.value:
                recommendations.append(f"移除 `{w.column}` 欄位（常數欄，無變異）")
            elif w.issue == IssueType.HIGH_CARDINALITY_ID.value:
                recommendations.append(f"排除 `{w.column}` 於分析（疑似 ID 欄位）")
            elif w.issue == IssueType.HIGH_MISSING.value:
                recommendations.append(f"處理 `{w.column}` 的缺失值（填補或移除）")
            elif w.issue == IssueType.SKEWED.value:
                recommendations.append(f"對 `{w.column}` 考慮使用 log transform")
            elif w.issue == IssueType.OUTLIERS.value:
                recommendations.append(f"檢查 `{w.column}` 的極端值")

        return recommendations

    def quick_check(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        快速品質檢查（輕量版）

        只返回最重要的資訊，適合快速預覽。

        Returns:
            dict: 包含 has_issues, critical_count, warning_count, issues_summary
        """
        report = self.analyze(df)

        critical_count = sum(1 for w in report.warnings if w.severity == IssueSeverity.CRITICAL.value)
        warning_count = sum(1 for w in report.warnings if w.severity == IssueSeverity.WARNING.value)
        info_count = sum(1 for w in report.warnings if w.severity == IssueSeverity.INFO.value)

        return {
            "has_issues": len(report.warnings) > 0,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "analysis_ready": report.analysis_readiness.ready,
            "usable_columns": len(report.analysis_readiness.usable_columns),
            "problematic_columns": len(report.analysis_readiness.problematic_columns),
            "issues_summary": [f"{w.issue}:{w.column}" for w in report.warnings],
        }


# 便捷函數
def analyze_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    便捷函數：分析資料品質

    Args:
        df: 要分析的 DataFrame

    Returns:
        dict: 品質報告字典
    """
    analyzer = DataQualityAnalyzer()
    report = analyzer.analyze(df)
    return report.to_dict()


def quick_quality_check(df: pd.DataFrame) -> Dict[str, Any]:
    """
    便捷函數：快速品質檢查

    Args:
        df: 要分析的 DataFrame

    Returns:
        dict: 快速檢查結果
    """
    analyzer = DataQualityAnalyzer()
    return analyzer.quick_check(df)
