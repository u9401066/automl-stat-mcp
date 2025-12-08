# MCP 工具架構審計清單

> **建立日期**: 2024-12-XX
> **目的**: 確保所有 MCP 工具遵循一致的架構模式

## 📐 架構概述

系統有 **兩種主要架構模式**：

### 模式 A: 服務架構 (Service Architecture)
```
MCP Server → HTTP → Service API → Redis Queue → Worker
```
- ✅ 適用於：長時間運算、需要持久化、需要 job 追蹤的任務
- 範例：EDA 報告、TableOne 生成、AutoML 訓練

### 模式 B: 直接調用 (Direct Import)
```
MCP Server → 直接 import 計算模組 → 同步返回結果
```
- ✅ 適用於：快速計算、無狀態操作、小型資料分析
- 範例：ROC 曲線計算、相關性分析、存活分析（使用 CSV 直傳）

---

## 🔍 審計發現

### ✅ 正確實作的工具

#### 1. AutoML 工具 (via automl-service)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `submit_automl_job` | training_tools.py | 服務架構 | ✅ |
| `submit_specific_job` | training_tools.py | 服務架構 | ✅ |
| `submit_compare_job` | training_tools.py | 服務架構 | ✅ |
| `get_job_status` | job_tools.py | 服務架構 | ✅ |
| `list_jobs` | job_tools.py | 服務架構 | ✅ |
| `cancel_job` | job_tools.py | 服務架構 | ✅ |
| `register_dataset` | dataset_tools.py | 服務架構 | ✅ |
| `list_datasets` | dataset_tools.py | 服務架構 | ✅ |
| `delete_dataset` | dataset_tools.py | 服務架構 | ✅ |
| `list_models` | model_tools.py | 服務架構 | ✅ |
| `get_model_leaderboard` | model_tools.py | 服務架構 | ✅ |
| `predict` | model_tools.py | 服務架構 | ✅ |
| `delete_model` | model_tools.py | 服務架構 | ✅ |

#### 2. 統計服務工具 (via stats-service → Redis → stats-worker)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `auto_analyze` | statistics_tools.py | 服務架構 | ✅ |
| `run_quick_auto_analyze` | statistics_tools.py | 服務架構 | ✅ |
| `submit_eda_job` | statistics_tools.py | 服務架構 | ✅ |
| `submit_tableone_job` | statistics_tools.py | 服務架構 | ✅ |
| `get_stats_job_status` | statistics_tools.py | 服務架構 | ✅ |
| `get_stats_job_result` | statistics_tools.py | 服務架構 | ✅ |
| `list_stats_jobs` | statistics_tools.py | 服務架構 | ✅ |
| `run_quick_eda` | statistics_tools.py | 服務架構 | ✅ |
| `run_quick_tableone` | statistics_tools.py | 服務架構 | ✅ |

#### 3. 直接分析工具 (Direct CSV → import stats-worker tasks)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `analyze_csv_directly` | statistics_tools.py | 直接調用 | ✅ (via stats_client) |
| `analyze_correlations` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `compare_groups` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `analyze_missing_values` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `check_multicollinearity` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `run_full_statistical_analysis` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `generate_tableone_directly` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |
| `get_tableone_preview` | statistics_tools.py | 直接調用 | ✅ (import stats_worker_tasks) |

#### 4. 存活分析工具 (Direct CSV → import survival_analysis)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `kaplan_meier_survival` | statistics_tools.py | 直接調用 | ✅ |
| `cox_proportional_hazards` | statistics_tools.py | 直接調用 | ✅ |
| `compare_survival` | statistics_tools.py | 直接調用 | ✅ |
| `survival_data_summary` | statistics_tools.py | 直接調用 | ✅ |

#### 5. Propensity Score 工具 (Direct CSV → import propensity_score)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `estimate_propensity_scores` | statistics_tools.py | 直接調用 | ✅ |
| `match_propensity_scores` | statistics_tools.py | 直接調用 | ✅ |
| `estimate_treatment_effect` | statistics_tools.py | 直接調用 | ✅ |
| `assess_covariate_balance` | statistics_tools.py | 直接調用 | ✅ |
| `run_propensity_analysis` | statistics_tools.py | 直接調用 | ✅ |

#### 6. ROC 分析工具 (Direct CSV → import roc_analysis)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `compute_roc_curve` | statistics_tools.py | 直接調用 | ✅ |
| `compare_roc_curves` | statistics_tools.py | 直接調用 | ✅ |
| `find_optimal_threshold` | statistics_tools.py | 直接調用 | ✅ |
| `analyze_calibration` | statistics_tools.py | 直接調用 | ✅ |
| `full_classifier_evaluation` | statistics_tools.py | 直接調用 | ✅ |
| `compare_multiple_roc_curves` | statistics_tools.py | 直接調用 | ✅ |
| `interactive_threshold_analysis` | statistics_tools.py | 直接調用 | ✅ |

#### 7. 直接 ML 工具 (via automl-service /direct endpoints)
| 工具 | 檔案 | 架構 | 狀態 |
|------|------|------|------|
| `direct_ml_analyze` | direct_tools.py | 服務架構 | ✅ |
| `direct_ml_quick_stats` | direct_tools.py | 服務架構 | ✅ |
| `direct_preview_data` | direct_tools.py | 服務架構 | ✅ |

---

## 🔑 關鍵架構橋接器

### `stats_worker_tasks.py`
這是 MCP Server 與 stats-worker 計算模組之間的橋接器：

```python
# 它透過 sys.path 直接 import stats-worker 的 tasks
stats_worker_path = os.path.join(..., 'stats-worker', 'src')
sys.path.insert(0, os.path.abspath(stats_worker_path))

from tasks.advanced_analysis import ...
from tasks.survival_analysis import ...
from tasks.propensity_score import ...
from tasks.roc_analysis import ...
```

**意義**：
- 對於 CSV 直傳的工具，MCP Server 直接 import 並調用 stats-worker 的函數
- 這避免了 HTTP + Redis Queue 的延遲，適合即時回應
- ⚠️ 但這表示 MCP Server 和 stats-worker 必須共享相同的 Python 環境

---

## 📊 架構選擇決策樹

```
工具需要什麼？
│
├─► 需要存取 MinIO 中的 dataset_id？
│   └─► 使用服務架構：MCP → stats-service → Redis → stats-worker
│       (例如: auto_analyze, submit_eda_job, submit_tableone_job)
│
├─► 直接傳入 CSV 內容？
│   └─► 使用直接調用：MCP → import stats_worker_tasks → 同步計算
│       (例如: compute_roc_curve, kaplan_meier_survival)
│
├─► 長時間運算 (>30秒)？
│   └─► 使用服務架構 + job 追蹤機制
│
└─► 簡單查詢/元資料？
    └─► 使用服務架構 (簡單 HTTP GET)
        (例如: list_algorithms, health_check)
```

---

## 🆕 Phase 6: Power Analysis 工具審計

### 建議架構

Power Analysis 工具特性：
- ✅ 無狀態計算
- ✅ 不需要存取 MinIO
- ✅ 計算速度快 (<1秒)
- ✅ 接受直接參數（非 CSV 檔案）

**結論**：應該使用 **直接調用架構**

### 正確實作方式

```
stats-worker/src/tasks/power_analysis.py
    ├── TTestPowerAnalysis (計算類)
    ├── ProportionPowerAnalysis (計算類)
    ├── ttest_power_analysis() (函數)
    └── proportion_power_analysis() (函數)
         ↑
         │ import
         │
automl-mcp-server/src/infrastructure/mcp/handlers/stats_worker_tasks.py
    └── from tasks.power_analysis import ...
         ↑
         │ import
         │
automl-mcp-server/src/infrastructure/mcp/handlers/statistics_tools.py
    └── @mcp.tool()
        async def calculate_ttest_power(...):
            from .stats_worker_tasks import ttest_power_analysis
            return ttest_power_analysis(...)
```

### 待辦事項

1. [x] `stats-worker/src/tasks/power_analysis.py` - 核心計算邏輯 ✅
2. [ ] `stats_worker_tasks.py` - 新增 import power_analysis
3. [ ] `statistics_tools.py` - 新增 MCP 工具包裝

---

## 📋 完整審計清單

### Handler 檔案審計狀態

| 檔案 | 用途 | 審計狀態 |
|------|------|----------|
| `training_tools.py` | AutoML 訓練 | ✅ 正確 |
| `job_tools.py` | Job 管理 | ✅ 正確 |
| `dataset_tools.py` | 資料集管理 | ✅ 正確 |
| `model_tools.py` | 模型管理 | ✅ 正確 |
| `direct_tools.py` | 直接 ML 分析 | ✅ 正確 |
| `info_tools.py` | 系統資訊 | ✅ 正確 |
| `smart_tools.py` | 智慧工作流程 | ✅ 正確 |
| `orchestration_tools.py` | 組合工具 | ✅ 正確 |
| `statistics_tools.py` | 統計分析 | ✅ 正確 |
| `stats_client.py` | HTTP 客戶端 | ✅ 正確 |
| `stats_worker_tasks.py` | Worker 橋接 | ⚠️ 需要新增 power_analysis |
| `data_cleaner.py` | 資料清洗 | ✅ 正確 (smart_tools 輔助模組) |
| `data_validator.py` | 資料驗證 | ✅ 正確 (smart_tools 輔助模組) |
| `base.py` | 基礎工具 | ✅ 正確 |

### Worker Tasks 審計狀態

| 檔案 | 用途 | 審計狀態 |
|------|------|----------|
| `advanced_analysis.py` | 進階統計分析 | ✅ 正確 |
| `auto_analyze_task.py` | 自動分析 | ✅ 正確 |
| `tableone_generator.py` | Table 1 生成 | ✅ 正確 |
| `survival_analysis.py` | 存活分析 | ✅ 正確 |
| `propensity_score.py` | 傾向分數 | ✅ 正確 |
| `roc_analysis.py` | ROC 曲線分析 | ✅ 正確 |
| `power_analysis.py` | 樣本量計算 | ✅ 正確 (新建) |

---

## ✅ 審計結論

### 架構一致性：**合格**

現有工具遵循兩種明確的架構模式：
1. **服務架構**：需要 MinIO 資料或長時間運算
2. **直接調用**：CSV 直傳的即時分析

### 需要修正的項目

1. **stats_worker_tasks.py**：新增 power_analysis import
2. **statistics_tools.py**：新增 Power Analysis MCP 工具

### Power Analysis 實作評估

目前 `stats-worker/src/tasks/power_analysis.py` 的實作**符合架構規範**：
- ✅ 純計算邏輯，無 IO 操作
- ✅ 直接使用 statsmodels（與 survival_analysis 等一致）
- ✅ 無狀態設計
- ✅ 可被 MCP Server 直接 import 使用

**無需重構**，只需完成橋接層和 MCP 工具註冊。

---

## 📅 後續行動

1. ✅ 確認 power_analysis.py 實作正確
2. [ ] 更新 stats_worker_tasks.py 新增 import
3. [ ] 更新 statistics_tools.py 新增 MCP 工具
4. [ ] 執行測試驗證
5. [ ] 審計 data_cleaner.py 和 data_validator.py
