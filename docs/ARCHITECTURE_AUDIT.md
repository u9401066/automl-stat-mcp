# 架構審查文件 (Architecture Audit)

> 建立日期：2025-01-13  
> 目的：檢查專案是否符合新的設計原則

## 🎯 核心設計原則

**Agent 只負責四件事：**
1. 傳入檔案路徑
2. 建立工單（含參數設定）
3. 查詢工單狀態
4. 取得輸出連結

**所有資料處理、計算、轉換都是 AutoML 系統內部的事！**

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

## ✅ 開始執行

準備好後，請告訴我：
1. **"開始 Phase 1"** - 我會開始新增 stats-service API
2. **"顯示 Phase 2 詳情"** - 我會列出要移除的工具清單
3. **"只做緊急修復"** - 我只移除 stats_worker_tasks.py，暫時不新增 API
