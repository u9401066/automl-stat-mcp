# 架構審查文件 (Architecture Audit)

> 建立日期：2025-01-13  
> 更新日期：2025-12-10  
> 目的：檢查專案是否符合新的設計原則

## 🎯 核心設計原則

**Agent 只負責四件事：**
1. 傳入檔案路徑
2. 建立工單（含參數設定）
3. 查詢工單狀態
4. 取得輸出連結

**所有資料處理、計算、轉換都是 AutoML 系統內部的事！**

---

## 📁 資料流向與儲存架構

### 目錄結構 (2025-12 更新)

```
workspace/
├── datasets/              # 原始資料 (read-only)
├── processed/             # 處理過的資料
│   └── {user_id}/
│       ├── data_20251210.csv
│       └── data_20251210_metadata.json
├── results/               # 📊 分析結果 (User 可直接查看)
│   └── {user_id}/
│       └── {job_name}_{timestamp}/
│           ├── metadata.json      # Job 資訊
│           ├── report.json        # 分析結果 JSON
│           ├── report.html        # 📄 HTML 報告 (人類可讀)
│           ├── figures/           # 📈 視覺化圖表
│           │   ├── roc_curve.png
│           │   ├── feature_importance.png
│           │   └── ...
│           └── data/
│               └── source_info.json  # 資料來源追蹤
├── sample_data/           # 範例資料集
└── uploads/               # 上傳的檔案
```

### 儲存位置對比

| 儲存位置 | 用途 | 存取方式 |
|----------|------|----------|
| **MinIO** (`stats-reports` bucket) | 雲端備份、API 存取 | Agent 透過 URL |
| **本地** (`/results/`) | User 直接瀏覽 | VS Code / 檔案總管 |

---

## 📊 目前狀態分析

### MCP 工具統計

| 位置 | 工具數量 | 狀態 |
|------|----------|------|
| `statistics_tools.py` | 56 | ⚠️ 需審查 |
| `upload_tools.py` | 3 | ✅ 符合設計 |
| `training_tools.py` | 3 | ✅ 符合設計 |
| `model_tools.py` | 4 | ✅ 符合設計 |
| `orchestration_tools.py` | 5+ | ⚠️ 需審查 |
| `job_tools.py` | ~3 | ✅ 符合設計 |
| `dataset_tools.py` | ~3 | ✅ 符合設計 |
| `info_tools.py` | ~2 | ✅ 符合設計 |
| `direct_tools.py` | ~3 | ⚠️ 需審查 |
| `smart_tools.py` | ~3 | ⚠️ 需審查 |
| **總計** | **~136** | ⚠️ 遠超過 18 核心工具 |

### Stats Service API Endpoints

| Router | Endpoints | 狀態 |
|--------|-----------|------|
| `auto_analyze.py` | /auto-analyze/* | ✅ 有 API |
| `direct.py` | /direct/* | ✅ 有 API |
| `eda.py` | /eda/* | ✅ 有 API |
| `tableone.py` | /tableone/* | ✅ 有 API |
| `jobs.py` | /jobs/* | ✅ 有 API |
| Propensity Score | ❌ 無 API | ❌ 需新增 |
| Survival Analysis | ❌ 無 API | ❌ 需新增 |
| ROC Analysis | ❌ 無 API | ❌ 需新增 |
| Power Analysis | ❌ 無 API | ❌ 需新增 |

---

## ✅ 修復進度

### Phase 1: 新增 stats-service API ✅ 完成

**新增的 Router 檔案：**

| 檔案 | Endpoints | 狀態 |
|------|-----------|------|
| `routes/propensity.py` | `/propensity/estimate/submit`, `/match/submit`, `/effect/submit`, `/balance/submit`, `/full/submit` | ✅ |
| `routes/survival.py` | `/survival/kaplan-meier/submit`, `/cox/submit`, `/compare/submit`, `/summary/submit` | ✅ |
| `routes/roc.py` | `/roc/compute/submit`, `/compare/submit`, `/threshold/submit`, `/calibration/submit`, `/full-eval/submit` | ✅ |
| `routes/power.py` | `/power/ttest`, `/proportion`, `/anova`, `/chi-square`, `/survival` | ✅ |

### Phase 2: 更新 stats_client.py ✅ 完成

**新增方法 (+25)：**
- Propensity: `submit_propensity_estimate_job`, `submit_propensity_match_job`, `submit_propensity_effect_job`, `submit_propensity_balance_job`, `submit_propensity_full_job`
- Survival: `submit_kaplan_meier_job`, `submit_cox_regression_job`, `submit_survival_compare_job`, `submit_survival_summary_job`
- ROC: `submit_roc_compute_job`, `submit_roc_compare_job`, `submit_roc_threshold_job`, `submit_roc_calibration_job`, `submit_roc_full_eval_job`, `submit_roc_compare_multiple_job`, `submit_roc_threshold_analysis_job`, `submit_roc_publication_report_job`
- Power: `calculate_ttest_power`, `calculate_proportion_power`, `calculate_anova_power`, `calculate_chisquare_power`, `calculate_survival_power`

### Phase 3: 更新 MCP Tools ✅ 完成

**修改的檔案：**

| 檔案 | 工具數 | 變更 |
|------|--------|------|
| `propensity_tools.py` | 5 | 改用 `stats_client.submit_propensity_*_job()` |
| `survival_tools.py` | 4 | 改用 `stats_client.submit_*_job()` |
| `roc_tools.py` | 8 | 改用 `stats_client.submit_roc_*_job()` |
| `power/ttest.py` | 7 | 改用 `stats_client.calculate_*_power()` |
| `power/anova.py` | 6 | 改用 `stats_client.calculate_*_power()` |
| `power/survival.py` | 5 | 改用 `stats_client.calculate_survival_power()` |

**關鍵修改：**
- ❌ 移除：`from .stats_worker_tasks import ...` (跨容器 import 失敗)
- ✅ 新增：`await stats_client.submit_*_job(...)` (HTTP API 調用)
- ✅ 保留：所有 docstrings 維護人員文件

### Phase 4: stats-worker Job 處理 ✅ 完成

**已新增 Job Types：**
- [x] `propensity_estimate`, `propensity_match`, `propensity_effect`, `propensity_balance`, `propensity_full`
- [x] `kaplan_meier`, `cox_regression`, `survival_compare`, `survival_summary`
- [x] `roc_compute`, `roc_compare`, `roc_threshold`, `roc_calibration`, `roc_full_eval`, `roc_compare_multiple`, `roc_threshold_analysis`, `roc_publication_report`
- [x] Power calculations (同步 API，不需要 worker queue)

**Worker 修改摘要：**
- `stats-worker/src/worker.py`: 新增 20+ job handler methods
- 修復 ROC function signature 問題 (y_scores vs y_score)
- 新增 `numpy` import for balance assessment

---

## 🗺️ ROADMAP: 方案 B - 統一入口模式

### 目標架構

將 136 個工具精簡為 ~10 個核心工具：

```python
# 1. 檔案管理
upload_dataset(path, storage_mode) → dataset_id

# 2. 統一分析入口 ⭐
submit_analysis_job(
    dataset_id: str,
    analysis_type: str,  # "auto", "tableone", "eda", "propensity", "survival", "roc", "power"
    config: dict,        # 各類型專屬參數 (JSON schema)
    user_id: str
) → job_id

# 3. 統一訓練入口 ⭐
submit_training_job(
    dataset_id: str,
    target_column: str,
    problem_type: str,   # "binary", "multiclass", "regression"
    config: dict,        # time_limit, presets, algorithms
    user_id: str
) → job_id

# 4. 工單管理
get_job_status(job_id) → status, progress
get_job_result(job_id) → result
list_jobs(user_id) → jobs[]

# 5. 模型使用
predict(model_id, dataset_id) → predictions

# 6. 資訊查詢
list_datasets(user_id) → datasets[]
list_models(user_id) → models[]
get_analysis_schema(analysis_type) → json_schema  # 告訴 Agent 該傳什麼參數
```

### 優點

1. **Agent 只需學習 10 個工具**（而非 136 個）
2. **參數由 JSON Schema 驅動**，LLM 可根據文檔生成
3. **擴展新分析類型不需新增工具**，只需新增 config schema
4. **減少 API 表面積**，更容易維護

### 實作時程

| Phase | 內容 | 預計時間 |
|-------|------|----------|
| Phase B1 | 設計 config JSON schemas | 2hr |
| Phase B2 | 實作 submit_analysis_job | 4hr |
| Phase B3 | 實作 get_analysis_schema | 2hr |
| Phase B4 | 遷移現有工具 | 4hr |
| Phase B5 | 更新文檔 | 2hr |

**總計：** ~14 小時

### Config Schema 範例

```json
{
  "analysis_type": "propensity",
  "config": {
    "treatment_column": "treatment",
    "outcome_column": "outcome",
    "covariates": ["age", "gender", "comorbidity"],
    "method": "matching",
    "caliper": 0.2,
    "estimand": "ATT"
  }
}
```

---

## 🔴 問題清單

### 問題 1: MCP 直接 import stats-worker 模組（嚴重）

**檔案：** `automl-mcp-server/src/infrastructure/mcp/handlers/stats_worker_tasks.py`

**問題：**
```python
# Line 11-12: 嘗試跨容器 import
stats_worker_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'stats-worker', 'src')
```

**影響：** 
- 在 Docker 環境中 import 必定失敗
- ~30 個工具返回 "stats-worker tasks not available"
- 包括：Propensity, Survival, ROC, Power Analysis

**解決方案：** 
- 移除此檔案
- 在 stats-service 新增對應的 API endpoints

---

### 問題 2: 工具數量過多（設計問題）

**發現：** 136 個 @mcp.tool() vs 設計目標 18 個

**影響：**
- Agent 混淆，不知道用哪個工具
- 維護困難
- 很多工具功能重疊

**解決方案：** Phase 2 精簡工具

---

### 問題 3: statistics_tools.py 過度膨脹

**檔案：** 3408 行，56 個工具

**問題：**
- 很多工具直接調用 stats_worker_tasks（會失敗）
- 混合了 API 調用和直接函數調用
- 違反單一職責

**解決方案：** Phase 3 重構

---

### 問題 4: 缺少統一的錯誤處理

**問題：**
- 有些工具返回 `{"error": "..."}`
- 有些工具拋出異常
- 沒有統一格式

**解決方案：** Phase 4 標準化

---

## ✅ 修復計畫

### Phase 1: 修復 stats-service API（優先！）

**目標：** 讓所有統計功能都透過 API 調用

1. **新增 Propensity Score API**
   - `POST /propensity/estimate` - 估計傾向分數
   - `POST /propensity/match` - 傾向分數配對
   - `POST /propensity/effect` - 估計處置效果
   - `POST /propensity/balance` - 評估平衡

2. **新增 Survival Analysis API**
   - `POST /survival/kaplan-meier` - KM 分析
   - `POST /survival/cox` - Cox 迴歸
   - `POST /survival/compare` - 比較存活曲線

3. **新增 ROC Analysis API**
   - `POST /roc/compute` - 計算 ROC 曲線
   - `POST /roc/compare` - 比較多個模型
   - `POST /roc/threshold` - 閾值分析

4. **新增 Power Analysis API**
   - `POST /power/ttest` - t-test 檢定力
   - `POST /power/proportion` - 比例檢定力
   - `POST /power/anova` - ANOVA 檢定力
   - `POST /power/survival` - 存活檢定力

**預計檔案：**
```
stats-service/src/routes/
├── propensity.py (新增)
├── survival.py (新增)
├── roc.py (新增)
└── power.py (新增)
```

---

### Phase 2: 精簡 MCP 工具

**目標：** 從 136 個減少到 ~25 個核心工具

**保留的核心工具：**

```
# 1. 檔案管理 (3)
- list_available_files
- upload_dataset
- get_upload_help

# 2. 資料集管理 (3)
- register_dataset
- list_datasets
- delete_dataset

# 3. 訓練管理 (3)
- submit_automl_job
- train_and_wait
- quick_train

# 4. 工單查詢 (3)
- get_job_status
- list_jobs
- wait_for_job

# 5. 模型管理 (4)
- list_models
- get_model_leaderboard
- predict
- delete_model

# 6. 統計分析 (5)
- submit_auto_analyze_job
- submit_tableone_job
- submit_eda_job
- get_stats_job_status
- get_stats_job_result

# 7. 進階分析 (4) - 需要 Phase 1 先完成
- submit_propensity_job
- submit_survival_job
- submit_roc_job
- submit_power_job

# 8. 資訊 (2)
- health_check
- list_algorithms

總計：27 個工具
```

**移除的工具：**
- 所有 "quick_*" 便利工具（整合到主工具）
- 所有 "run_*" 同步等待工具（改用 wait_for_job）
- 所有 "analyze_*" 直接計算工具（改用提交工單）
- 所有 "calculate_*" 本地計算工具（改用 API）

---

### Phase 3: 重構 statistics_tools.py

**目標：** 拆分成多個小檔案，每個只負責調用 API

**新結構：**
```
handlers/
├── statistics/
│   ├── __init__.py
│   ├── auto_analyze.py      # 自動分析相關
│   ├── tableone.py          # Table 1 相關
│   ├── eda.py               # EDA 相關
│   ├── propensity.py        # 傾向分數相關
│   ├── survival.py          # 存活分析相關
│   ├── roc.py               # ROC 分析相關
│   └── power.py             # 檢定力分析相關
├── stats_client.py          # HTTP Client（擴充）
└── stats_worker_tasks.py    # 刪除！
```

---

### Phase 4: 標準化錯誤處理

**目標：** 統一所有工具的返回格式

**成功格式：**
```json
{
  "success": true,
  "job_id": "xxx",
  "message": "Job submitted successfully"
}
```

**失敗格式：**
```json
{
  "success": false,
  "error": "Error message",
  "error_code": "INVALID_DATASET"
}
```

---

## 📋 執行順序

| Phase | 內容 | 預計時間 | 依賴 |
|-------|------|----------|------|
| Phase 1 | 新增 stats-service API | 4-6 小時 | 無 |
| Phase 2 | 精簡 MCP 工具 | 2-3 小時 | Phase 1 |
| Phase 3 | 重構 statistics_tools | 2-3 小時 | Phase 2 |
| Phase 4 | 標準化錯誤處理 | 1-2 小時 | Phase 3 |

**總預計時間：** 9-14 小時

---

## 🚦 Phase 1 詳細任務

### 任務 1.1: 新增 propensity.py router

**檔案：** `stats-service/src/routes/propensity.py`

**Endpoints：**
```python
@router.post("/submit")
async def submit_propensity_job(
    dataset_id: str,
    user_id: str,
    treatment_column: str,
    covariates: List[str],
    method: str = "logistic",  # logistic, gbm, random_forest
) -> dict:
    """提交傾向分數分析工單"""

@router.post("/match")  
async def submit_matching_job(
    dataset_id: str,
    user_id: str,
    treatment_column: str,
    propensity_column: str = None,  # 已有的傾向分數欄位
    method: str = "nearest",  # nearest, caliper, optimal
    caliper: float = 0.2,
) -> dict:
    """提交傾向分數配對工單"""
```

### 任務 1.2: 新增 survival.py router

**檔案：** `stats-service/src/routes/survival.py`

**Endpoints：**
```python
@router.post("/kaplan-meier/submit")
async def submit_km_job(
    dataset_id: str,
    user_id: str,
    time_column: str,
    event_column: str,
    group_column: str = None,
) -> dict:
    """提交 Kaplan-Meier 分析工單"""

@router.post("/cox/submit")
async def submit_cox_job(
    dataset_id: str,
    user_id: str,
    time_column: str,
    event_column: str,
    covariates: List[str],
) -> dict:
    """提交 Cox 迴歸工單"""
```

### 任務 1.3: 新增 roc.py router

**檔案：** `stats-service/src/routes/roc.py`

**Endpoints：**
```python
@router.post("/compute/submit")
async def submit_roc_job(
    dataset_id: str,
    user_id: str,
    true_column: str,
    pred_column: str,
    model_name: str = "Model",
) -> dict:
    """提交 ROC 分析工單"""

@router.post("/compare/submit")
async def submit_roc_compare_job(
    dataset_id: str,
    user_id: str,
    true_column: str,
    pred_columns: List[str],
    model_names: List[str] = None,
) -> dict:
    """提交 ROC 比較工單"""
```

### 任務 1.4: 新增 power.py router

**檔案：** `stats-service/src/routes/power.py`

**Endpoints：**
```python
@router.post("/ttest")
async def calculate_ttest_power(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.8,
    alternative: str = "two-sided",
    ratio: float = 1.0,
) -> dict:
    """計算 t-test 所需樣本數或檢定力"""

@router.post("/proportion")
async def calculate_proportion_power(
    p1: float,
    p2: float,
    alpha: float = 0.05,
    power: float = 0.8,
) -> dict:
    """計算比例檢定所需樣本數"""
```

---

## 🔍 詳細問題分析

### 受影響的檔案清單

**直接依賴 stats_worker_tasks.py 的檔案：**

| 檔案 | 問題工具數 | 狀態 |
|------|-----------|------|
| `statistics/propensity_tools.py` | 5 | ❌ 全部壞掉 |
| `statistics/survival_tools.py` | 4 | ❌ 全部壞掉 |
| `statistics/roc_tools.py` | 9 | ❌ 全部壞掉 |
| `statistics/tableone_tools.py` | 1 (部分) | ⚠️ 部分壞掉 |
| `statistics/power/ttest.py` | 7 | ❌ 全部壞掉 |
| `statistics/power/anova.py` | 6 | ❌ 全部壞掉 |
| `statistics/power/survival.py` | 4 | ❌ 全部壞掉 |
| `statistics_tools_backup.py` | ~40 | 📦 備份檔案，可刪除 |

**總計：** ~36 個工具在 Docker 環境中壞掉

### 問題根因

```python
# statistics/propensity_tools.py:70
from .stats_worker_tasks import estimate_propensity_scores as _estimate_ps
```

`stats_worker_tasks.py` 嘗試：
```python
stats_worker_path = os.path.join(..., 'stats-worker', 'src')
sys.path.insert(0, os.path.abspath(stats_worker_path))
from tasks.propensity_score import ...  # ❌ 在 Docker 中失敗
```

### 正確的架構應該是

```
Agent → MCP Tool → stats_client.py → HTTP → stats-service API → Redis Queue → stats-worker
```

而不是：
```
Agent → MCP Tool → stats_worker_tasks.py (直接 import) ❌
```

---

## ✅ 開始執行

準備好後，請告訴我：
1. **"開始 Phase 1"** - 我會開始新增 stats-service API
2. **"顯示 Phase 2 詳情"** - 我會列出要移除的工具清單
3. **"只做緊急修復"** - 我只移除 stats_worker_tasks.py，暫時不新增 API
