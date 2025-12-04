# Phase 6: Power Analysis / Sample Size - Implementation Plan

> 💡 **臨床研究第一步**：在收集資料前就需要計算樣本量

## Overview

Power Analysis 是臨床研究設計的核心步驟，在收集資料前就需要計算：
- 需要多少樣本才能偵測到有意義的差異
- 給定樣本量時，研究有多大的統計功效

---

## 分階段實作計劃

### Phase 6.1: 基礎雙組比較 (Foundation)
**預計測試數: 30-40**

| 功能 | 描述 | 使用套件 |
|------|------|----------|
| Two-sample t-test | 兩組平均數比較的樣本量 | statsmodels |
| Paired t-test | 配對設計的樣本量 | statsmodels |
| Two proportions | 兩組比例比較 (chi-square) | statsmodels |
| One-sample tests | 單組檢定樣本量 | statsmodels |

**MCP Tools:**
- `calculate_ttest_sample_size` - t檢定樣本量計算
- `calculate_proportion_sample_size` - 比例檢定樣本量計算

**輸入參數範例:**
```python
# t-test
{
    "effect_size": 0.5,      # Cohen's d (small=0.2, medium=0.5, large=0.8)
    "alpha": 0.05,           # 顯著水準
    "power": 0.80,           # 統計功效
    "alternative": "two-sided",
    "ratio": 1.0             # n2/n1 比例
}

# Proportion test
{
    "p1": 0.30,              # 組1預期比例
    "p2": 0.50,              # 組2預期比例
    "alpha": 0.05,
    "power": 0.80,
    "alternative": "two-sided"
}
```

---

### Phase 6.2: 多組比較與相關性 (Multi-group)
**預計測試數: 25-30**

| 功能 | 描述 | 使用套件 |
|------|------|----------|
| One-way ANOVA | 多組平均數比較 | statsmodels |
| Chi-square test | 多組類別比較 | statsmodels |
| Correlation test | 相關性檢定 | statsmodels |

**MCP Tools:**
- `calculate_anova_sample_size` - ANOVA 樣本量
- `calculate_correlation_sample_size` - 相關性檢定樣本量

---

### Phase 6.3: 存活分析樣本量 (Survival)
**預計測試數: 25-30**

| 功能 | 描述 | 使用套件 |
|------|------|----------|
| Log-rank test | 兩組存活曲線比較 | lifelines/自製 |
| Cox regression | Cox 模型的樣本量 | lifelines/自製 |

**MCP Tools:**
- `calculate_logrank_sample_size` - Log-rank 樣本量
- `calculate_cox_sample_size` - Cox 回歸樣本量

**臨床場景:**
```python
# 生存研究設計
{
    "hazard_ratio": 0.7,     # 風險比 (治療 vs 對照)
    "median_survival_control": 12,  # 對照組中位生存月數
    "accrual_time": 24,      # 收案期間 (月)
    "follow_up_time": 12,    # 追蹤期間 (月)
    "dropout_rate": 0.10,    # 脫落率
    "alpha": 0.05,
    "power": 0.80
}
```

---

### Phase 6.4: 非劣性/等效性試驗 (NI/Equivalence)
**預計測試數: 25-30**

| 功能 | 描述 | 使用套件 |
|------|------|----------|
| Non-inferiority (continuous) | 連續變數非劣性 | statsmodels |
| Non-inferiority (binary) | 二元變數非劣性 | statsmodels |
| Equivalence (TOST) | 等效性檢定 | statsmodels |

**MCP Tools:**
- `calculate_non_inferiority_sample_size` - 非劣性樣本量
- `calculate_equivalence_sample_size` - 等效性樣本量

**臨床場景:**
```python
# 非劣性試驗 (藥物比較)
{
    "p_reference": 0.70,     # 參照藥物成功率
    "p_test": 0.70,          # 試驗藥物預期成功率
    "margin": 0.10,          # 非劣性邊界
    "alpha": 0.025,          # 單側檢定
    "power": 0.80
}
```

---

### Phase 6.5: 事後功效與報告 (Post-hoc & Reporting)
**預計測試數: 20-25**

| 功能 | 描述 | 使用套件 |
|------|------|----------|
| Post-hoc power | 事後功效計算 | statsmodels |
| Effect size from data | 從資料估計效應量 | scipy |
| Power report | 完整報告生成 | 自製 |

**MCP Tools:**
- `calculate_post_hoc_power` - 事後功效分析
- `estimate_effect_size` - 效應量估計
- `generate_power_report` - 樣本量報告生成

---

## 整體 MCP 工具清單

| Phase | Tool | Description |
|-------|------|-------------|
| 6.1 | `calculate_ttest_sample_size` | t檢定樣本量 |
| 6.1 | `calculate_proportion_sample_size` | 比例檢定樣本量 |
| 6.2 | `calculate_anova_sample_size` | ANOVA 樣本量 |
| 6.2 | `calculate_correlation_sample_size` | 相關性樣本量 |
| 6.3 | `calculate_logrank_sample_size` | Log-rank 樣本量 |
| 6.3 | `calculate_cox_sample_size` | Cox 回歸樣本量 |
| 6.4 | `calculate_non_inferiority_sample_size` | 非劣性樣本量 |
| 6.4 | `calculate_equivalence_sample_size` | 等效性樣本量 |
| 6.5 | `calculate_post_hoc_power` | 事後功效 |
| 6.5 | `estimate_effect_size` | 效應量估計 |
| 6.5 | `generate_power_report` | 報告生成 |

**Total: 11 MCP tools, ~130-155 tests**

---

## 技術實作細節

### 使用套件

```python
# 核心依賴
from statsmodels.stats.power import (
    TTestIndPower,
    TTestPower,
    NormalIndPower,
    FTestAnovaPower,
    GofChisquarePower,
)
from statsmodels.stats.proportion import proportion_effectsize
import scipy.stats as stats
```

### 檔案結構

```
stats-worker/src/tasks/
├── power_analysis.py          # Phase 6.1-6.2: 基礎功效分析
├── survival_power.py          # Phase 6.3: 存活分析樣本量
├── non_inferiority_power.py   # Phase 6.4: 非劣性/等效性
└── power_report.py            # Phase 6.5: 報告生成

stats-worker/tests/
├── test_power_analysis.py
├── test_survival_power.py
├── test_non_inferiority_power.py
└── test_power_report.py
```

### 輸出格式 (統一)

```python
@dataclass
class PowerAnalysisResult:
    """Power analysis result"""
    test_type: str               # "t-test", "proportion", "anova", etc.
    scenario: str                # "sample_size" or "power"
    
    # 計算結果
    sample_size_per_group: Optional[int]
    total_sample_size: Optional[int]
    power: Optional[float]
    
    # 輸入參數
    parameters: Dict[str, Any]
    
    # 效應量資訊
    effect_size: Optional[float]
    effect_size_type: str        # "Cohen's d", "Cohen's h", "f", etc.
    effect_size_interpretation: str  # "small", "medium", "large"
    
    # 敏感度分析
    sensitivity_analysis: Optional[Dict]  # power curves
    
    # 臨床解讀
    interpretation: str
    recommendations: List[str]
```

---

## 時程估計

| Phase | 工作天 | 累計 |
|-------|--------|------|
| Phase 6.1 | 2 | 2 |
| Phase 6.2 | 1.5 | 3.5 |
| Phase 6.3 | 2 | 5.5 |
| Phase 6.4 | 2 | 7.5 |
| Phase 6.5 | 1.5 | 9 |

**總計: ~9 工作天**

---

## 臨床應用場景

### 場景 1: RCT 樣本量計算
```
醫師: "我要做一個 RCT 比較新藥和舊藥，預期新藥有效率 70%，舊藥 50%，
      要 80% power 和 5% alpha，需要多少人？"

Agent: calculate_proportion_sample_size(p1=0.5, p2=0.7, power=0.8, alpha=0.05)
→ 每組需要 62 人，總共 124 人
```

### 場景 2: 生存研究設計
```
醫師: "我要比較兩種化療方案，對照組中位存活 12 個月，
      希望偵測到 HR=0.7 的差異，收案 2 年追蹤 1 年"

Agent: calculate_logrank_sample_size(
    hazard_ratio=0.7,
    median_survival_control=12,
    accrual_time=24,
    follow_up_time=12
)
→ 需要約 200 個事件，建議收案 280 人 (考慮 15% 脫落)
```

### 場景 3: 非劣性試驗
```
藥廠: "我們的學名藥要證明不比原廠藥差，非劣性邊界 10%"

Agent: calculate_non_inferiority_sample_size(
    p_reference=0.75,
    margin=0.10,
    alpha=0.025
)
→ 每組需要 294 人
```

---

## 開始實作

要開始 Phase 6.1 嗎？我會：
1. 創建 `stats-worker/src/tasks/power_analysis.py`
2. 實作 t-test 和 proportion 樣本量計算
3. 創建完整測試套件
4. 更新 worker.py 整合新功能
