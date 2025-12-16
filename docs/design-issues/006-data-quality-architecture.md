# 資料品質分析與 Transform 架構設計

## 📋 概述

本文件描述資料品質檢測和 Transform 建議的推薦架構，
基於 `test_data_quality.py` 中的測試發現。

---

## 🔍 目前系統能力分析

### ✅ 可以偵測的問題

| 問題類型 | 偵測方式 | 目前狀態 |
|----------|----------|----------|
| 全 NaN 欄 | `null == rows` | ✅ 可偵測 |
| 常數欄 | `unique == 1` | ✅ 可偵測 |
| 高基數 ID 欄 | `unique == rows` | ✅ 可偵測 |
| 偏態資料 | `mean >> median` | ✅ 可計算 |
| 極端值 | `max > Q3 + 1.5*IQR` | ✅ 可計算 |

### ⚠️ 需要改進的部分

1. **沒有 quality_warnings 欄位** - 使用者需要自己判斷
2. **沒有 Transform 建議** - 偏態資料需要手動處理
3. **沒有分析可行性評估** - 不會提示資料不適合分析

---

## 🏗️ 推薦架構

### 1. 新增 DataQualityAnalyzer 模組

```python
# stats-service/src/domain/services/data_quality.py

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

@dataclass
class QualityWarning:
    column: str
    issue: str  # ALL_NAN, CONSTANT, HIGH_CARDINALITY_ID, SKEWED, OUTLIERS
    severity: str  # critical, warning, info
    recommendation: str
    impact: str
    stats: Dict[str, Any]

@dataclass
class TransformSuggestion:
    column: str
    suggested_transform: str  # log, sqrt, box_cox, none
    reason: str
    before_stats: Dict[str, float]
    after_preview: Optional[Dict[str, float]]

@dataclass
class DataQualityReport:
    warnings: List[QualityWarning]
    transform_suggestions: List[TransformSuggestion]
    analysis_ready: bool
    blocking_issues: List[str]
    recommended_actions: List[str]


class DataQualityAnalyzer:
    """資料品質分析器"""
    
    # 閾值設定
    SKEW_THRESHOLD = 1.0  # mean/median ratio
    HIGH_CARDINALITY_THRESHOLD = 0.9  # unique/rows ratio
    OUTLIER_IQR_MULTIPLIER = 1.5
    
    def analyze(self, df: pd.DataFrame) -> DataQualityReport:
        """完整資料品質分析"""
        warnings = []
        transform_suggestions = []
        blocking_issues = []
        
        for col in df.columns:
            # 檢查全 NaN
            if df[col].isna().all():
                warnings.append(QualityWarning(
                    column=col,
                    issue="ALL_NAN",
                    severity="critical",
                    recommendation="移除此欄或填補缺失值",
                    impact="此欄不會被納入任何統計分析",
                    stats={"null_count": len(df), "null_pct": 100.0}
                ))
                blocking_issues.append(f"ALL_NAN:{col}")
                continue
            
            # 檢查常數欄
            if df[col].nunique() == 1:
                warnings.append(QualityWarning(
                    column=col,
                    issue="CONSTANT",
                    severity="warning",
                    recommendation="移除此欄，無分析價值",
                    impact="常數欄的相關性為 NaN，無法用於迴歸或分組",
                    stats={"unique": 1, "value": df[col].dropna().iloc[0]}
                ))
                continue
            
            # 檢查高基數 ID 欄
            cardinality_ratio = df[col].nunique() / len(df)
            if cardinality_ratio >= self.HIGH_CARDINALITY_THRESHOLD:
                if df[col].dtype == 'object':
                    warnings.append(QualityWarning(
                        column=col,
                        issue="HIGH_CARDINALITY_ID",
                        severity="warning",
                        recommendation="排除於統計分析外",
                        impact="不適合作為分類或分組變數",
                        stats={"unique": df[col].nunique(), "cardinality_ratio": cardinality_ratio}
                    ))
            
            # 檢查偏態（僅數值欄）
            if pd.api.types.is_numeric_dtype(df[col]):
                mean = df[col].mean()
                median = df[col].median()
                if median > 0:
                    skew_ratio = abs(mean - median) / median
                    if skew_ratio > self.SKEW_THRESHOLD:
                        warnings.append(QualityWarning(
                            column=col,
                            issue="SKEWED",
                            severity="info",
                            recommendation="考慮 log transform 或使用非參數方法",
                            impact="參數統計方法（如 t-test）可能不準確",
                            stats={"mean": mean, "median": median, "skew_ratio": skew_ratio}
                        ))
                        
                        # 建議 Transform
                        if (df[col] > 0).all():  # 可以取 log
                            log_values = np.log(df[col])
                            transform_suggestions.append(TransformSuggestion(
                                column=col,
                                suggested_transform="log",
                                reason=f"嚴重正偏態 (skew_ratio={skew_ratio:.2f})",
                                before_stats={"mean": mean, "median": median},
                                after_preview={
                                    "mean": log_values.mean(),
                                    "median": log_values.median()
                                }
                            ))
        
        # 評估分析可行性
        analysis_ready = len(blocking_issues) == 0
        
        # 生成建議動作
        recommended_actions = []
        for w in warnings:
            if w.severity == "critical":
                recommended_actions.append(f"移除 {w.column} 欄位")
            elif w.issue == "HIGH_CARDINALITY_ID":
                recommended_actions.append(f"排除 {w.column} 於分析")
            elif w.issue == "SKEWED":
                recommended_actions.append(f"對 {w.column} 應用 log transform")
        
        return DataQualityReport(
            warnings=warnings,
            transform_suggestions=transform_suggestions,
            analysis_ready=analysis_ready,
            blocking_issues=blocking_issues,
            recommended_actions=recommended_actions
        )
```

### 2. 整合到現有端點

```python
# 修改 direct.py 的 QuickStatsResponse

class QuickStatsResponse(BaseModel):
    rows: int
    columns: int
    column_info: List[dict]
    missing_summary: dict
    numeric_summary: Optional[dict]
    
    # 新增欄位
    quality_warnings: Optional[List[dict]] = None
    transform_suggestions: Optional[List[dict]] = None
    analysis_readiness: Optional[dict] = None
```

### 3. 新增專用端點

```python
# POST /direct/quality-check
@router.post("/quality-check")
async def quality_check(request: QuickStatsRequest):
    """
    🔍 資料品質檢查
    
    偵測資料品質問題並提供建議：
    - 全 NaN 欄
    - 常數欄  
    - 高基數 ID 欄
    - 偏態資料
    - 極端值
    
    Returns:
        quality_warnings: 品質警告列表
        transform_suggestions: Transform 建議
        analysis_readiness: 分析可行性評估
    """
    ...
```

---

## 📊 Transform 支援

### 目前支援的 Transform

| Transform | 適用情況 | 注意事項 |
|-----------|----------|----------|
| Log | 正偏態、收入/價格資料 | 所有值必須 > 0 |
| Log1p | 含 0 的正偏態資料 | log(x+1) |
| Sqrt | 輕度偏態 | 所有值必須 >= 0 |
| Box-Cox | 需要自動選擇 | 需要 scipy |
| Z-score | 標準化 | 不改變分佈形狀 |

### 實作建議

```python
def apply_transform(df: pd.DataFrame, col: str, transform: str) -> pd.Series:
    """應用 Transform"""
    if transform == "log":
        return np.log(df[col])
    elif transform == "log1p":
        return np.log1p(df[col])
    elif transform == "sqrt":
        return np.sqrt(df[col])
    elif transform == "box_cox":
        from scipy.stats import boxcox
        transformed, _ = boxcox(df[col] + 1)  # 加 1 避免 0
        return pd.Series(transformed)
    elif transform == "zscore":
        return (df[col] - df[col].mean()) / df[col].std()
    else:
        return df[col]
```

---

## 🎯 統計分析對問題資料的處理

### 目前行為

| 分析類型 | 全 NaN 欄 | 常數欄 | 偏態資料 |
|----------|-----------|--------|----------|
| Quick Stats | ✅ 返回 null=100% | ✅ std=0 | ✅ 可計算 |
| Table One | ⚠️ 會跳過 | ⚠️ 無變異 | ⚠️ 可指定 nonnormal |
| Correlation | ❌ 產生 NaN | ❌ 產生 NaN | ✅ 正常 |
| Survival | ❌ 500 Error | ⚠️ 可能失敗 | ✅ 正常 |
| Propensity | ❌ Job Failed | ⚠️ 估計不穩 | ✅ 正常 |
| ROC | ⚠️ AUC=0.5 | ⚠️ AUC=0.5 | ✅ 正常 |

### 改進建議

1. **前置檢查**：在分析前檢查資料品質，提前返回警告
2. **優雅降級**：遇到問題時返回部分結果 + 警告
3. **使用者引導**：明確告知哪些欄位有問題、如何處理

---

## 🧪 測試覆蓋

已建立 `test_data_quality.py`，包含 25 個測試：

```
TestAllNaNColumns (3 tests)
TestConstantColumns (3 tests)  
TestHighCardinalityIDColumns (2 tests)
TestSkewedDataNeedingTransform (2 tests)
TestOutliers (1 test)
TestMixedTypes (2 tests)
TestStatisticalAnalysisRobustness (7 tests)
TestDataQualityRecommendations (2 tests)
TestTransformRequirements (2 tests)
TestRecommendedArchitecture (1 test - documentation)
```

---

## 📝 後續開發計畫

### Phase 1: 品質警告（優先）
- [ ] 實作 `DataQualityAnalyzer`
- [ ] 在 `quick-stats` 返回 `quality_warnings`
- [ ] 在 MCP 的 `smart_analyze` 整合

### Phase 2: Transform 支援
- [ ] 新增 `/direct/transform` 端點
- [ ] 支援 log, log1p, sqrt, box_cox
- [ ] 返回 transform 前後的比較

### Phase 3: 自動清理
- [ ] 新增 `/direct/auto-clean` 端點
- [ ] 自動移除全 NaN 欄
- [ ] 自動排除高基數 ID 欄
- [ ] 提供清理後的資料

---

## 🔗 相關文件

- [test_data_quality.py](../tests/test_data_quality.py) - 測試套件
- [direct.py](../stats-service/src/routes/direct.py) - Direct 分析路由
- [004-tool-consolidation-plan.md](./design-issues/004-tool-consolidation-plan.md) - 工具整合計畫
