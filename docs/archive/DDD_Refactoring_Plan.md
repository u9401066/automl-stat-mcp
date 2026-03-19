# DDD 重構計畫

## 代碼品質分析報告

### 超過 500 行的文件列表

| 文件 | 行數 | 類型 | 問題 | 優先級 |
|------|------|------|------|--------|
| `statistics_tools.py` | 3407 | MCP Handler | 58個工具混在一個文件，違反 SRP | 🔴 高 |
| `power_analysis.py` | 2827 | Domain Logic | 3種不同類型的 Power Analysis 混合 | 🔴 高 |
| `roc_analysis.py` | 1961 | Domain Logic | 多個分析器類別可拆分 | 🟡 中 |
| `propensity_score.py` | 1258 | Domain Logic | 結構良好，可接受 | 🟢 低 |
| `advanced_analysis.py` | 1201 | Domain Logic | 功能混雜，需拆分 | 🟡 中 |
| `survival_analysis.py` | 1058 | Domain Logic | 結構良好，可接受 | 🟢 低 |
| `tableone_generator.py` | 1035 | Domain Logic | 結構良好，可接受 | 🟢 低 |
| `test_roc_analysis.py` | 911 | Tests | 測試文件，可接受 | 🟢 低 |
| `auto_analyze_task.py` | 860 | Application | 可拆分為更小的 use cases | 🟡 中 |
| `data_validator.py` | 800 | Infrastructure | 驗證規則可拆分 | 🟡 中 |
| `smart_tools.py` | 589 | MCP Handler | 可接受 | 🟢 低 |

---

## 重構計畫

### Phase R1: statistics_tools.py 拆分 (最高優先)

**問題：** 3407 行，58 個 MCP 工具全部在一個文件中

**目標結構：**
```
automl-mcp-server/src/infrastructure/mcp/handlers/
├── statistics/
│   ├── __init__.py
│   ├── base.py                    # 共用工具、錯誤處理
│   ├── eda_tools.py               # EDA 相關 (5 tools)
│   ├── tableone_tools.py          # TableOne 相關 (3 tools)
│   ├── survival_tools.py          # Survival Analysis (4 tools)
│   ├── propensity_tools.py        # Propensity Score (5 tools)
│   ├── roc_tools.py               # ROC/AUC Analysis (7 tools)
│   └── power_analysis/
│       ├── __init__.py
│       ├── ttest_tools.py         # T-test Power (4 tools)
│       ├── proportion_tools.py    # Proportion Power (4 tools)
│       ├── anova_tools.py         # ANOVA Power (3 tools)
│       ├── chisquare_tools.py     # Chi-square Power (3 tools)
│       └── survival_tools.py      # Survival Power (5 tools)
```

**預估：** 每個文件 200-400 行

---

### Phase R2: power_analysis.py 拆分

**問題：** 2827 行，包含 T-test, Proportion, ANOVA, Chi-square, Survival 5種分析

**目標結構：**
```
stats-worker/src/tasks/power_analysis/
├── __init__.py                    # 統一導出
├── base.py                        # 共用 dataclass, enums, utils (~150 lines)
├── ttest.py                       # TTestPowerAnalysis (~400 lines)
├── proportion.py                  # ProportionPowerAnalysis (~350 lines)
├── anova.py                       # ANOVAPowerAnalysis (~450 lines)
├── chisquare.py                   # ChiSquarePowerAnalysis (~450 lines)
└── survival.py                    # SurvivalPowerAnalysis (~700 lines)
```

**預估：** 每個文件 150-700 行

---

### Phase R3: advanced_analysis.py 拆分

**問題：** 1201 行，多種不相關的分析功能混合

**目標結構：**
```
stats-worker/src/tasks/analysis/
├── __init__.py
├── correlation.py                 # 相關性分析
├── distribution.py                # 分佈比較
├── missing_data.py                # 缺失值分析
├── multicollinearity.py           # VIF 分析
└── enhanced_analysis.py           # 整合分析
```

---

### Phase R4: roc_analysis.py 拆分

**問題：** 1961 行，多個 Analyzer 類別

**目標結構：**
```
stats-worker/src/tasks/roc/
├── __init__.py
├── base.py                        # ROCPoint, ROCCurveResult
├── analyzer.py                    # ROCAnalyzer
├── delong.py                      # DeLongTest
├── calibration.py                 # CalibrationAnalyzer
├── precision_recall.py            # PrecisionRecallAnalyzer
├── net_benefit.py                 # NetBenefitAnalyzer
└── publication.py                 # 報告生成
```

---

## DDD 原則應用

### Domain Layer (stats-worker/src/tasks/)
- **單一職責：** 每個文件處理一種統計分析
- **領域模型：** 使用 dataclass 定義領域物件
- **無外部依賴：** 純 Python + 科學計算庫

### Application Layer (stats-service/src/application/)
- **Use Cases：** 協調多個 domain services
- **DTOs：** 定義 API 交互格式

### Infrastructure Layer (automl-mcp-server/)
- **MCP Tools：** 薄適配層，調用 domain services
- **錯誤處理：** 統一錯誤格式

---

## 重構時程

| Phase | 內容 | 預估時間 | 風險 |
|-------|------|----------|------|
| R1 | statistics_tools.py 拆分 | 4-6 小時 | 中（需更新所有導入） |
| R2 | power_analysis.py 拆分 | 2-3 小時 | 低（內部模組） |
| R3 | advanced_analysis.py 拆分 | 2 小時 | 低 |
| R4 | roc_analysis.py 拆分 | 2 小時 | 低 |

**總計：** 10-13 小時

---

## 重構原則

1. **向後兼容：** 保持現有 API 不變
2. **漸進式：** 一次只重構一個模組
3. **測試驅動：** 每次重構後運行完整測試
4. **文檔同步：** 更新 README 和 Memory Bank

---

## 暫不重構的文件

以下文件雖然行數較多，但結構良好或為測試文件：

- `propensity_score.py` (1258 lines) - 結構清晰，職責單一
- `survival_analysis.py` (1058 lines) - 符合 DDD
- `tableone_generator.py` (1035 lines) - 功能內聚
- `test_*.py` - 測試文件，行數合理

---

## 代碼品質指標目標

| 指標 | 當前 | 目標 |
|------|------|------|
| 最大文件行數 | 3407 | < 800 |
| 平均文件行數 | ~600 | < 400 |
| 文件數量 | 少但大 | 多但小 |
| 模組內聚度 | 低 | 高 |

---

*建立日期：2024-12-04*
*狀態：計畫中*
