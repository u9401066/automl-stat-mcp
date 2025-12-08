# AutoML MCP Server - 工具清單與使用指南

## 📊 工具總覽

| 模組 | 工具數量 | 狀態 | 說明 |
|------|----------|------|------|
| Upload | 3 | ✅ 可用 | 資料上傳與檔案列表 |
| Dataset | 3 | ✅ 可用 | 資料集管理 |
| Training | 3 | ✅ 可用 | AutoML 訓練 |
| Job | 3 | ✅ 可用 | 訓練任務管理 |
| Model | 2 | ✅ 可用 | 模型管理 |
| Orchestration | 5 | ✅ 可用 | 工作流編排 |
| EDA/Auto-Analyze | 14 | ⚠️ 部分可用 | 探索性資料分析 |
| TableOne | 5 | ⚠️ 部分可用 | 統計表格生成 |
| Survival | 4 | ❌ 不可用 | 生存分析 |
| Propensity | 5 | ❌ 不可用 | 傾向分數分析 |
| ROC/AUC | 8 | ⚠️ 部分可用 | ROC 曲線分析 |
| Power Analysis | 19 | ⚠️ 部分可用 | 檢定力分析 |
| Stats Jobs | 3 | ✅ 可用 | 統計任務管理 |

**總計: ~77 工具 (但許多因 import 問題無法使用)**

---

## 🚨 關鍵問題

### 問題 1: stats-worker 模組無法在 MCP 容器中 import

```
WARNING - Could not import stats-worker tasks: No module named 'tasks'
```

**原因**: MCP Server (automl-mcp) 和 Stats Worker (stats-worker) 是獨立容器，MCP 嘗試直接 import stats-worker 程式碼失敗。

**影響的工具**:
- 所有 Propensity Score 工具 (5個)
- 所有 Survival Analysis 工具 (4個)
- 部分 ROC/Calibration 工具
- 部分 Power Analysis 工具

**解決方案**:
1. 統計工具應該透過 API 呼叫 stats-service，而非直接 import
2. 或者將 stats-worker 程式碼打包成 Python package

---

### 問題 2: 工具依賴關係複雜，Agent 難以正確串接

**正確的工作流程**:
```
1. list_available_files()     → 看有什麼檔案
2. upload_dataset()           → 上傳/註冊資料集 → 取得 dataset_id
3. analyze_dataset()          → 分析資料集特性
4. submit_automl_job()        → 開始訓練 → 取得 job_id
5. get_job_status()           → 輪詢直到完成 → 取得 model_id
6. get_model_leaderboard()    → 查看結果
7. predict()                  → 預測新資料
```

**Agent 容易犯的錯誤**:
- 沒有 dataset_id 就嘗試訓練
- 沒有等待 job 完成就查詢結果
- 使用需要 CSV content 的工具但用錯格式

---

## ✅ 完全可用的工具 (推薦使用)

### 1. 上傳與檔案管理
```python
# 列出可用檔案
list_available_files(directory="/data/sample_data")

# 上傳資料集 (永久存檔)
upload_dataset(
    name="my_data",
    source_type="local",
    source_path="/data/sample_data/titanic.csv",
    storage_mode="permanent",
    user_id="user1"
)  # → 返回 dataset_id

# 查看上傳說明
get_upload_help()
```

### 2. 資料集管理
```python
# 列出已註冊的資料集
list_datasets(user_id="user1")

# 刪除資料集
delete_dataset(dataset_id="xxx", user_id="user1")
```

### 3. AutoML 訓練
```python
# 提交 AutoML 訓練
submit_automl_job(
    dataset_id="xxx",
    target_column="survived",
    problem_type="binary",
    user_id="user1",
    presets="medium_quality",
    time_limit=300
)  # → 返回 job_id

# 提交特定算法訓練
submit_specific_job(
    dataset_id="xxx",
    target_column="survived",
    problem_type="binary",
    algorithms=["XGB", "RF", "GBM"],
    user_id="user1"
)

# 比較多個算法
submit_compare_job(
    dataset_id="xxx",
    target_column="survived",
    problem_type="binary",
    algorithms=["XGB", "GBM", "RF", "NN_TORCH"],
    user_id="user1"
)
```

### 4. 任務管理
```python
# 查詢任務狀態
get_job_status(job_id="xxx", user_id="user1")

# 等待任務完成
wait_for_job(job_id="xxx", user_id="user1", timeout=3600)

# 列出所有任務
list_jobs(user_id="user1")
```

### 5. 模型管理
```python
# 查看排行榜
get_model_leaderboard(model_id="xxx", user_id="user1")

# 預測
predict(model_id="xxx", dataset_id="yyy", user_id="user1")
```

### 6. 統計分析 (透過 stats-service API)
```python
# TableOne - 透過 API
submit_tableone_job(
    dataset_id="xxx",
    user_id="user1",
    groupby="survived",
    categorical=["sex", "pclass"],
    nonnormal=["age", "fare"],
    pval=True
)  # → 返回 job_id

# 查詢統計任務狀態
get_stats_job_status(job_id="xxx")

# 取得統計結果
get_stats_job_result(job_id="xxx")
```

---

## ⚠️ 部分可用的工具 (需注意)

### Direct CSV 分析工具

這些工具需要直接傳入 CSV 內容，適合小型資料：

```python
# 快速統計 (同步)
get_quick_stats(csv_content="col1,col2\n1,2\n3,4")

# 完整分析 (同步)
run_full_statistical_analysis(
    csv_content="...",
    target_column="target"
)

# 生成 TableOne (同步)
generate_tableone_directly(
    csv_content="...",
    groupby="group",
    categorical=["cat1", "cat2"],
    pval=True
)
```

---

## ❌ 目前無法使用的工具

### Propensity Score Analysis (傾向分數)
- `estimate_propensity_scores` - ❌ Module not available
- `match_propensity_scores` - ❌ Module not available
- `estimate_treatment_effect` - ❌ Module not available
- `assess_covariate_balance` - ❌ Module not available
- `run_propensity_analysis` - ❌ Module not available

### Survival Analysis (生存分析)
- `kaplan_meier_survival` - ❌ Module not available
- `cox_proportional_hazards` - ❌ Module not available
- `compare_survival` - ❌ Module not available
- `survival_data_summary` - ❌ Module not available

---

## 🔧 建議的修復方案

### 方案 A: 統一透過 stats-service API (推薦)

將 MCP 的統計工具改為呼叫 stats-service REST API，而非直接 import：

```python
# 修改前 (直接 import)
from .stats_worker_tasks import estimate_propensity_scores

# 修改後 (呼叫 API)
async def estimate_propensity_scores(...):
    response = await stats_client.post("/stats/propensity/estimate", json={...})
    return response.json()
```

### 方案 B: 建立 shared Python package

將 stats-worker/src/tasks 打包成 Python package 並安裝到 MCP 容器。

### 方案 C: 精簡工具數量

移除無法使用的工具，只保留可靠的工具：
- 保留: Upload, Dataset, Training, Job, Model, TableOne (via API)
- 移除或重構: Propensity, Survival, ROC (direct), Power

---

## 📋 給 Agent 的提示模板

建議在 MCP instruction 中加入：

```
## AutoML MCP 使用流程

### 步驟 1: 上傳資料
必須先呼叫 upload_dataset() 取得 dataset_id，才能進行後續操作。

### 步驟 2: 訓練模型
使用 submit_automl_job() 開始訓練，這是非同步操作。

### 步驟 3: 等待完成
使用 wait_for_job() 或重複呼叫 get_job_status() 直到 status="completed"。

### 步驟 4: 查看結果
使用 get_model_leaderboard() 查看訓練結果。

### 重要提醒
- 沒有 dataset_id 不能訓練
- 沒有 job 完成不能查結果
- 統計分析使用 submit_tableone_job (非同步) 或 generate_tableone_directly (同步)
- Propensity Score 和 Survival Analysis 工具目前不可用
```

---

## 📈 後續改進計劃

### 優先級 1: 精簡工具 (短期)
1. [ ] 移除無法使用的 Propensity/Survival/Power 工具 (或改為 "coming soon" 提示)
2. [ ] 確保保留的工具都能正常運作
3. [ ] 更新 Agent 提示，只列出可用的工具

### 優先級 2: 擴展 stats-service API (中期)
1. [ ] 新增 `/propensity/*` endpoints
2. [ ] 新增 `/survival/*` endpoints
3. [ ] 新增 `/roc/*` endpoints
4. [ ] 新增 `/power/*` endpoints
5. [ ] MCP 工具改為呼叫這些 API

### 優先級 3: 改善 Agent 體驗 (持續)
1. [ ] 增加工具的錯誤提示，說明缺少什麼前置條件
2. [ ] 加入工作流程驗證，防止錯誤的呼叫順序
3. [ ] 提供更好的範例和文件

---

## 🎯 精簡後的推薦工具清單

如果要立即發布，建議只保留以下工具：

| 工具 | 用途 | 依賴 |
|------|------|------|
| `health_check` | 檢查服務狀態 | 無 |
| `list_available_files` | 列出可用檔案 | 無 |
| `get_upload_help` | 上傳說明 | 無 |
| `upload_dataset` | 上傳資料集 | 無 → dataset_id |
| `list_datasets` | 列出資料集 | 無 |
| `delete_dataset` | 刪除資料集 | dataset_id |
| `analyze_dataset` | 分析資料集 | dataset_id |
| `submit_automl_job` | AutoML 訓練 | dataset_id → job_id |
| `submit_specific_job` | 特定算法訓練 | dataset_id → job_id |
| `submit_compare_job` | 比較算法 | dataset_id → job_id |
| `get_job_status` | 查詢任務狀態 | job_id |
| `wait_for_job` | 等待任務完成 | job_id → model_id |
| `list_jobs` | 列出任務 | 無 |
| `get_model_leaderboard` | 查看排行榜 | model_id |
| `predict` | 預測 | model_id, dataset_id |
| `submit_tableone_job` | TableOne 統計 | dataset_id → job_id |
| `get_stats_job_status` | 統計任務狀態 | job_id |
| `get_stats_job_result` | 統計結果 | job_id |

**總計: 18 個核心工具** (從 77 個精簡到 18 個)
