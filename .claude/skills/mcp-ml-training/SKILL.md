---
name: mcp-ml-training
description: Machine learning model training workflow using AutoML including data upload, model training, evaluation, and prediction. Use when training classification or regression models, comparing algorithms, or making predictions on new data. Triggers: 訓練模型, train model, ML, 機器學習, AutoML, prediction, 預測, classification, regression, 分類, 迴歸, XGBoost, random forest, neural network, 模型比較.
---

# ML Training Workflow 技能 (機器學習訓練流程)

## 描述
使用 AutoML MCP 工具進行機器學習模型訓練的完整流程。

## 觸發條件
- 「訓練模型」「train model」
- 「用 {dataset} 預測 {target}」
- 「AutoML」「機器學習」

---

## 🎯 訓練流程總覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ML Training Workflow                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] 資料準備        →  upload_dataset / register_dataset          │
│         ↓                                                           │
│   [2] 提交訓練        →  submit_automl_job / quick_train            │
│         ↓                                                           │
│   [3] 監控進度        →  get_job_status / wait_for_job              │
│         ↓                                                           │
│   [4] 取得結果        →  get_model_leaderboard / get_job_result     │
│         ↓                                                           │
│   [5] 使用模型        →  predict                                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: 資料準備

### 1.1 列出可用資料

```python
# 列出本地檔案
mcp_automl_list_available_files(
    directory="/data/sample_data"
)
```

### 1.2 上傳/註冊資料集

**方式 A：本地檔案上傳（推薦）**

```python
mcp_automl_upload_dataset(
    name="my_titanic",
    source_type="local",
    source_path="/data/sample_data/titanic.csv",
    storage_mode="permanent",  # permanent: 永久存到 MinIO
    user_id="eric"
)
# 返回: dataset_id
```

**方式 B：從 MinIO 註冊**

```python
mcp_automl_register_dataset(
    name="my_dataset",
    minio_path="datasets/my_data.csv",
    user_id="eric"
)
```

### 1.3 分析資料集特性

```python
mcp_automl_analyze_dataset(
    dataset_id="dataset-xxx"
)
```

---

## 📋 Step 2: 提交訓練工作

### 2.1 完整 AutoML 訓練（推薦）

```python
result = mcp_automl_submit_automl_job(
    dataset_id="dataset-xxx",
    target_column="survived",
    problem_type="binary",      # binary, multiclass, regression
    time_limit=300,             # 秒，預設 300
    presets="medium_quality",   # best_quality, high_quality, medium_quality, optimize_for_deployment
    user_id="eric"
)
job_id = result["job_id"]
```

**presets 選擇指南：**

| Preset | 訓練時間 | 準確度 | 適用場景 |
|--------|----------|--------|----------|
| `best_quality` | 最長 | 最高 | 競賽、論文 |
| `high_quality` | 長 | 高 | 生產環境 |
| `medium_quality` | 中等 | 中等 | 開發測試 |
| `optimize_for_deployment` | 短 | 中等 | 部署優先 |

### 2.2 快速訓練（一鍵完成）

```python
# 簡化版：自動等待完成
result = mcp_automl_quick_train(
    csv_path="/data/sample_data/titanic.csv",
    target_column="survived",
    user_id="eric"
)
# 直接返回 model_id 和結果
```

### 2.3 指定特定演算法

```python
# 列出可用演算法
mcp_automl_list_algorithms()
# 返回: GBM, CAT, XGB, RF, XT, KNN, LR, NN_TORCH, FASTAI

# 指定演算法訓練
mcp_automl_submit_specific_job(
    dataset_id="dataset-xxx",
    target_column="survived",
    algorithms=["XGB", "RF", "GBM"],
    user_id="eric"
)
```

### 2.4 比較多個演算法

```python
mcp_automl_submit_compare_job(
    dataset_id="dataset-xxx",
    target_column="survived",
    algorithms=["XGB", "GBM", "RF", "NN_TORCH"],
    user_id="eric"
)
```

---

## 📋 Step 3: 監控訓練進度

### 3.1 查詢工作狀態

```python
mcp_automl_get_job_status(
    job_id="job-xxx",
    user_id="eric"
)
```

**狀態說明：**

| 狀態 | 說明 |
|------|------|
| `pending` | 等待中 |
| `running` | 訓練中 |
| `completed` | 完成 |
| `failed` | 失敗 |

### 3.2 等待訓練完成

```python
# 同步等待（會阻塞直到完成）
result = mcp_automl_wait_for_job(
    job_id="job-xxx",
    timeout=600,  # 最長等待秒數
    user_id="eric"
)
```

### 3.3 列出所有工作

```python
mcp_automl_list_jobs(
    user_id="eric"
)
```

### 3.4 取消工作

```python
mcp_automl_cancel_job(
    job_id="job-xxx",
    user_id="eric"
)
```

---

## 📋 Step 4: 取得訓練結果

### 4.1 取得模型排行榜

```python
mcp_automl_get_model_leaderboard(
    model_id="model-xxx"
)
```

**輸出範例：**
```json
{
  "leaderboard": [
    {"model": "WeightedEnsemble_L2", "score_val": 0.87},
    {"model": "XGBoost", "score_val": 0.85},
    {"model": "LightGBM", "score_val": 0.84}
  ],
  "best_model": "WeightedEnsemble_L2",
  "metrics": {
    "accuracy": 0.82,
    "roc_auc": 0.87,
    "f1": 0.79
  }
}
```

### 4.2 取得訓練摘要

```python
mcp_automl_get_training_summary(
    model_id="model-xxx"
)
```

### 4.3 列出所有模型

```python
mcp_automl_list_models(
    user_id="eric"
)
```

---

## 📋 Step 5: 使用模型預測

### 5.1 使用已訓練模型預測

```python
mcp_automl_predict(
    model_id="model-xxx",
    dataset_id="new-data-xxx",  # 新資料集
    user_id="eric"
)
```

**或直接用 CSV 路徑：**

```python
mcp_automl_predict(
    model_id="model-xxx",
    csv_path="/data/projects/my_project/new_data.csv",
    user_id="eric"
)
```

---

## 🎯 完整範例

### 範例 1：Titanic 二元分類

```
User: "用 titanic.csv 預測 survived"

Agent 執行：

1. 列出檔案確認存在
   mcp_automl_list_available_files(directory="/data/sample_data")
   
2. 上傳資料集
   mcp_automl_upload_dataset(
       name="titanic_train",
       source_type="local",
       source_path="/data/sample_data/titanic.csv",
       storage_mode="permanent",
       user_id="eric"
   )
   → dataset_id: "dataset-abc123"

3. 提交訓練
   mcp_automl_submit_automl_job(
       dataset_id="dataset-abc123",
       target_column="survived",
       problem_type="binary",
       time_limit=300,
       presets="medium_quality",
       user_id="eric"
   )
   → job_id: "job-xyz789"

4. 等待完成
   mcp_automl_wait_for_job(
       job_id="job-xyz789",
       user_id="eric"
   )
   → model_id: "model-def456"

5. 取得結果
   mcp_automl_get_model_leaderboard(model_id="model-def456")
   
回報使用者：
"✅ 訓練完成！
最佳模型：WeightedEnsemble_L2
準確率：82%
AUC-ROC：0.87

排行榜：
1. WeightedEnsemble_L2 (0.87)
2. XGBoost (0.85)
3. LightGBM (0.84)"
```

### 範例 2：快速訓練

```
User: "快速訓練一個模型，用 iris.csv 預測 species"

Agent 執行：

mcp_automl_quick_train(
    csv_path="/data/sample_data/iris.csv",
    target_column="species",
    user_id="eric"
)

回報使用者：
"✅ 快速訓練完成！
最佳模型：{model_name}
準確率：{accuracy}%"
```

### 範例 3：比較演算法

```
User: "比較 XGBoost、LightGBM、Random Forest 在 heart_disease 上的表現"

Agent 執行：

1. mcp_automl_upload_dataset(
       name="heart_disease",
       source_path="/data/sample_data/heart_disease.csv",
       ...
   )

2. mcp_automl_submit_compare_job(
       dataset_id="...",
       target_column="target",
       algorithms=["XGB", "GBM", "RF"],
       user_id="eric"
   )

3. mcp_automl_wait_for_job(...)

4. mcp_automl_get_model_leaderboard(...)

回報使用者：
"📊 演算法比較結果：

| 演算法 | AUC | 準確率 |
|--------|-----|--------|
| XGBoost | 0.89 | 85% |
| LightGBM | 0.88 | 84% |
| Random Forest | 0.86 | 83% |

建議使用 XGBoost 作為最終模型。"
```

---

## 📊 可用演算法

| 代碼 | 演算法 | 說明 |
|------|--------|------|
| GBM | LightGBM | 梯度提升（快速） |
| CAT | CatBoost | 類別特徵友好 |
| XGB | XGBoost | 梯度提升（經典） |
| RF | Random Forest | 隨機森林 |
| XT | Extra Trees | 極端隨機樹 |
| KNN | K-Nearest Neighbors | K 近鄰 |
| LR | Linear Model | 線性模型 |
| NN_TORCH | Neural Network | PyTorch 神經網路 |
| FASTAI | FastAI NN | FastAI 神經網路 |

---

## ⚠️ 常見錯誤

### 1. 未等待訓練完成

```python
# ❌ 錯誤：提交後直接取結果
submit_automl_job(...)
get_model_leaderboard(...)  # 會失敗！

# ✅ 正確：等待完成
job = submit_automl_job(...)
wait_for_job(job["job_id"])  # 等待
get_model_leaderboard(...)   # 成功
```

### 2. 目標欄位名稱錯誤

```python
# 先確認欄位名稱
mcp_automl_get_column_info(csv_path="...")
# 再使用正確名稱
```

### 3. 忘記 user_id

```python
# 大多數操作都需要 user_id
submit_automl_job(..., user_id="eric")
```
