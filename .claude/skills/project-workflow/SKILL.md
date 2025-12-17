---
name: project-workflow
description: Complete project workflow from creation to report generation. Covers project setup, data upload, quality check, analysis execution, and result delivery. Use when user wants to run a full research project or needs guidance on the standard operating procedure. Triggers: 新專案, 建立專案, 完整流程, 研究流程, full workflow, project setup, 從頭開始, start project, SOP, 標準流程.
---

# Project Workflow 技能 (專案完整操作流程)

## 描述
AutoML 專案從建立到報告產生的完整標準操作流程 (SOP)。

## 觸發條件
- 「新專案」「建立專案」「從頭開始」
- 「完整流程」「研究流程」「SOP」
- 「正式分析」「發表用」

---

## ⚠️ 重要提醒（執行前必讀）

### 路徑規則（最常犯錯！）

| 環境 | 路徑前綴 | 使用時機 |
|------|----------|----------|
| Container | `/data/sample_data/` | MCP 工具參數 |
| Container | `/data/projects/` | 使用者專案資料 |
| Host | `/home/eric/...` | ❌ 禁止用於 MCP |

```python
# ❌ 錯誤
csv_path="/home/eric/workspace251204/sample_data/iris.csv"

# ✅ 正確
csv_path="/data/sample_data/iris.csv"
```

### 預設參數

```python
# 除非使用者指定，一律使用：
user_id = "eric"
storage_mode = "temporary"  # 快速分析用
```

---

## 🎯 標準流程總覽

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    AutoML 專案標準操作流程 (SOP)                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 0: 檢視可用資料                                            │   │
│   │  ├─ list_available_files("/data/sample_data")                   │   │
│   │  └─ quick_preview("filename.csv")                               │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 1: 建立專案目錄 (可選，正式研究用)                          │   │
│   │  └─ create_project_workspace(project_name, user_id, template)   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 2: 上傳/移動資料                                           │   │
│   │  ├─ upload_dataset(source_path, storage_mode="temporary")       │   │
│   │  └─ upload_dataset(source_path, storage_mode="permanent")       │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 3: 資料品質檢查                                            │   │
│   │  ├─ quality_check(csv_path)                                     │   │
│   │  └─ quick_stats(csv_path, include_quality_check=True)           │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 4: 執行分析/訓練                                           │   │
│   │  ├─ [分析] smart_analyze / generate_tableone_directly           │   │
│   │  ├─ [統計] kaplan_meier / cox / roc_curve                       │   │
│   │  └─ [ML] submit_automl_job → wait_for_job → get_leaderboard    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 5: 取得結果                                                │   │
│   │  ├─ list_analysis_results(user_id)                              │   │
│   │  ├─ get_analysis_result(result_id)                              │   │
│   │  └─ get_model_leaderboard(model_id)                             │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │  Step 6: 產生報告 (可選)                                         │   │
│   │  └─ generate_analysis_report(result_ids)                        │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 0: 檢視可用資料

### 目的
了解有什麼資料可以使用，預覽資料結構。

### 執行工具

```python
# 列出目錄檔案
list_available_files(directory="/data/sample_data")

# 快速預覽（自動路徑轉換）
quick_preview(csv_path="iris.csv")
# 或完整路徑
quick_preview(csv_path="/data/sample_data/iris.csv")
```

### 輸出
- 檔案清單
- 行數、欄數
- 欄位名稱和型別
- 缺失值概況

### 可用範例資料集

| 檔案 | 類型 | 目標變數 | 適用場景 |
|------|------|----------|----------|
| `iris.csv` | 多類別分類 | species | ML 入門 |
| `titanic.csv` | 二元分類 | survived | ML 入門 |
| `heart_disease.csv` | 二元分類 | target | 醫學 ML |
| `breast_cancer.csv` | 二元分類 | diagnosis | 醫學 ML |
| `medical_study_200.csv` | RCT 資料 | treatment_group | 臨床研究 |
| `rossi_recidivism.csv` | 存活資料 | arrest, week | 存活分析 |
| `stanford_heart.csv` | 存活資料 | status, time | 存活分析 |
| `california_housing.csv` | 迴歸 | median_house_value | 迴歸預測 |
| `wine_quality.csv` | 分類/迴歸 | quality | 品質預測 |

---

## 📋 Step 1: 建立專案目錄（可選）

### 目的
為正式研究建立組織良好的目錄結構。

### 何時需要
- ✅ 正式研究專案
- ✅ 多次分析的專案
- ✅ 需要保留結果的專案
- ❌ 快速探索性分析（可跳過）

### 執行工具

```python
create_project_workspace(
    project_name="my_breast_cancer_study",
    user_id="eric",
    template="medical_study"  # 模板選項見下方
)
```

### 模板選項

| 模板 | 目錄結構 | 適用場景 |
|------|----------|----------|
| `default` | data/, analysis/, reports/ | 一般用途 |
| `medical_study` | data/raw/, data/processed/, analysis/, reports/, figures/ | 臨床研究 |
| `ml_project` | data/, models/, notebooks/, src/ | ML 專案 |

### 產生目錄結構

```
/data/projects/my_breast_cancer_study/
├── data/
│   ├── raw/           # 放原始資料
│   └── processed/     # 放清理後資料
├── analysis/          # 分析結果
├── reports/           # 報告
└── figures/           # 圖表
```

---

## 📋 Step 2: 上傳/移動資料

### 目的
將資料上傳到系統中供分析使用。

### 儲存模式選擇

| 模式 | 儲存位置 | 保留時間 | 適用場景 |
|------|----------|----------|----------|
| `temporary` | Redis | 7 天 | 快速分析、探索 |
| `permanent` | MinIO | 永久 | 正式研究、ML 訓練 |

### 執行工具

**暫存模式（快速分析）：**
```python
upload_dataset(
    name="quick_analysis",
    source_type="local",
    source_path="/data/sample_data/breast_cancer.csv",
    storage_mode="temporary",
    user_id="eric"
)
# 返回: job_id（用於單次分析）
```

**永久模式（正式研究）：**
```python
upload_dataset(
    name="breast_cancer_study",
    source_type="local",
    source_path="/data/projects/my_study/data/raw/data.csv",
    storage_mode="permanent",
    user_id="eric"
)
# 返回: dataset_id（用於 ML 訓練和重複分析）
```

### ⚠️ 注意事項
- ML 訓練**必須**使用 `permanent` 模式
- 路徑必須用 `/data/...` 開頭

---

## 📋 Step 3: 資料品質檢查

### 目的
分析前檢查資料品質，發現潛在問題。

### 執行工具

**專用品質檢查：**
```python
quality_check(csv_path="/data/sample_data/breast_cancer.csv")
```

**整合在 quick_stats：**
```python
quick_stats(
    csv_path="/data/sample_data/breast_cancer.csv",
    include_quality_check=True
)
```

### 輸出說明

**quality_warnings（品質警告）：**
| 類型 | 嚴重度 | 說明 | 建議處理 |
|------|--------|------|----------|
| ALL_NAN | critical | 全空值欄位 | 移除欄位 |
| CONSTANT | warning | 常數欄位 | 移除欄位 |
| HIGH_CARDINALITY_ID | warning | 高基數 ID | 移除欄位 |
| HIGH_MISSING | warning | 缺失率 >30% | 填補或移除 |
| SKEWED | info | 偏態分布 | 考慮轉換 |
| OUTLIERS | info | 極端異常值 | 檢查資料 |

**transform_suggestions（轉換建議）：**
| 類型 | 適用情況 | 說明 |
|------|----------|------|
| log | 正偏態、全正值 | 對數轉換 |
| log1p | 正偏態、含零 | log(1+x) 轉換 |
| zscore | 正偏態、含負值 | Z-score 標準化 |

**analysis_readiness（分析準備度）：**
| 狀態 | 意義 |
|------|------|
| ready | 可直接分析 |
| needs_review | 建議先處理警告 |
| not_ready | 有嚴重問題需處理 |

---

## 📋 Step 4: 執行分析/訓練

### 路徑 A：描述性分析

**推薦！一站式分析：**
```python
smart_analyze(
    csv_path="breast_cancer.csv",
    group_column="diagnosis"  # 可選：分組比較
)
# 返回: stats + tableone + correlations
```

**分步執行：**
```python
# Step 4a: 基本統計
quick_stats(csv_path="breast_cancer.csv")

# Step 4b: Table One（分組比較）
generate_tableone_directly(
    csv_path="breast_cancer.csv",
    group_column="diagnosis"
)
# 返回: result_id

# Step 4c: 相關性分析
analyze_correlations(csv_path="breast_cancer.csv")
```

### 路徑 B：統計分析

**存活分析：**
```python
# Kaplan-Meier 曲線
kaplan_meier_survival(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_col="week",
    event_col="arrest",
    group_col="fin"  # 可選：分組比較
)

# Cox 比例風險模型
cox_proportional_hazards(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_col="week",
    event_col="arrest",
    covariates=["age", "prio", "fin"]
)
```

**ROC 分析：**
```python
compute_roc_curve(
    csv_path="predictions.csv",
    y_true_col="target",
    y_score_col="probability"
)
```

**傾向分數配對：**
```python
run_propensity_analysis(
    csv_path="medical_study.csv",
    treatment_col="treatment_group",
    covariates=["age", "sex", "bmi"]
)
```

### 路徑 C：機器學習

**Step 4a: 提交訓練（必須先 upload_dataset 為 permanent）**
```python
submit_automl_job(
    dataset_id="dataset-xxx",  # 來自 upload_dataset
    target_column="diagnosis",
    problem_type="binary",     # binary / multiclass / regression
    time_limit=300,            # 秒
    presets="medium_quality",  # 品質預設
    user_id="eric"
)
# 返回: job_id
```

**Step 4b: 等待完成**
```python
wait_for_job(
    job_id="job-xxx",
    user_id="eric"
)
# 返回: model_id
```

**Step 4c: 查看結果**
```python
get_model_leaderboard(
    model_id="model-xxx",
    user_id="eric"
)
```

**快速訓練（一鍵完成）：**
```python
quick_train(
    csv_path="/data/sample_data/heart_disease.csv",
    target_column="target",
    user_id="eric"
)
# 自動完成: 上傳 → 訓練 → 等待 → 返回結果
```

---

## 📋 Step 5: 取得結果

### 列出所有結果
```python
list_analysis_results(
    user_id="eric",
    analysis_type="tableone"  # 可選過濾
)
```

### 取得特定結果
```python
get_analysis_result(result_id="stat_tableone_abc123")
```

### ML 模型排行榜
```python
get_model_leaderboard(model_id="model-xxx", user_id="eric")
```

### 結果儲存位置
| 類型 | Redis Key | MinIO 路徑 |
|------|-----------|------------|
| TableOne | `stats:result:stat_tableone_xxx` | `automl-results/eric/tableone/` |
| ROC | `stats:result:stat_roc_xxx` | `automl-results/eric/roc/` |
| Correlation | `stats:result:stat_correlation_xxx` | `automl-results/eric/correlation/` |
| ML Model | - | `automl-results/eric/models/` |

---

## 📋 Step 6: 產生報告（可選）

### 執行工具
```python
generate_analysis_report(
    result_ids=["stat_tableone_xxx", "stat_roc_yyy"],
    user_id="eric"
)
```

### 輸出
- Markdown 報告
- 儲存於: `automl-results/eric/reports/`

---

## 🎯 快速決策樹

```
使用者需求
    │
    ├─→ 「看看這個資料」
    │       └─→ Step 0 → Step 3
    │           quick_preview → quality_check
    │
    ├─→ 「快速分析」「幫我分析一下」
    │       └─→ Step 0 → Step 2(暫存) → Step 4A
    │           quick_preview → upload(temp) → smart_analyze
    │
    ├─→ 「正式研究」「要發表的」
    │       └─→ Step 0 → Step 1 → Step 2(永久) → Step 3 → Step 4 → Step 5 → Step 6
    │           完整流程
    │
    ├─→ 「訓練模型」「預測」
    │       └─→ Step 0 → Step 2(永久) → Step 4C → Step 5
    │           quick_preview → upload(permanent) → submit_automl_job → wait → leaderboard
    │
    ├─→ 「存活分析」「KM 曲線」
    │       └─→ Step 0 → Step 4B
    │           quick_preview → kaplan_meier_survival
    │
    └─→ 「比較兩組」「治療效果」
            └─→ Step 0 → Step 4A (with group_column)
                quick_preview → smart_analyze(group_column="treatment")
```

---

## 📊 完整範例

### 範例 1：快速探索分析

```
User: "幫我分析 breast_cancer.csv"

Agent 執行：
1. quick_preview(csv_path="breast_cancer.csv")
   → 569 rows, 32 columns, diagnosis 為二元變數

2. smart_analyze(
       csv_path="breast_cancer.csv",
       group_column="diagnosis"
   )
   → 返回: stats + tableone + correlations

回報使用者：
"📊 乳腺癌資料分析完成！

資料概況：
- 樣本數：569 (M: 212, B: 357)
- 變數數：32

主要發現：
- 惡性(M)組的 radius_mean 顯著較高 (p<0.001)
- texture_mean 與 radius_mean 呈高度相關 (r=0.32)

Result ID: stat_tableone_abc123"
```

### 範例 2：正式研究專案

```
User: "我要做一個心臟病預測的正式研究"

Agent 執行：
1. create_project_workspace(
       project_name="heart_disease_study_2025",
       user_id="eric",
       template="medical_study"
   )
   → /data/projects/heart_disease_study_2025/

2. upload_dataset(
       name="heart_disease_main",
       source_path="/data/sample_data/heart_disease.csv",
       storage_mode="permanent",
       user_id="eric"
   )
   → dataset_id: "dataset-xxx"

3. quality_check(csv_path="/data/sample_data/heart_disease.csv")
   → analysis_readiness: "ready"

4. generate_tableone_directly(
       csv_path="/data/sample_data/heart_disease.csv",
       group_column="target"
   )
   → result_id: "stat_tableone_yyy"

5. submit_automl_job(
       dataset_id="dataset-xxx",
       target_column="target",
       problem_type="binary",
       time_limit=600,
       presets="high_quality",
       user_id="eric"
   )
   → job_id: "job-zzz"

6. wait_for_job(job_id="job-zzz", user_id="eric")
   → model_id: "model-aaa"

7. get_model_leaderboard(model_id="model-aaa", user_id="eric")

8. generate_analysis_report(
       result_ids=["stat_tableone_yyy"],
       user_id="eric"
   )

回報使用者：
"✅ 心臟病研究專案建立完成！

📁 專案目錄: /data/projects/heart_disease_study_2025/

📊 基線特徵 Table One:
| 變數 | No Disease (n=164) | Disease (n=139) | p-value |
|------|-------------------|-----------------|---------|
| Age | 52.6 ± 9.8 | 56.8 ± 8.1 | 0.001 |
| Sex (M) | 89 (54%) | 107 (77%) | <0.001 |

🤖 ML 模型結果:
| 模型 | AUC | 準確率 |
|------|-----|--------|
| WeightedEnsemble_L2 | 0.91 | 87% |
| XGBoost | 0.89 | 85% |

📄 報告已儲存: automl-results/eric/reports/"
```

---

## ⚠️ 常見錯誤

### 1. 路徑錯誤
```python
# ❌ 用了 Host 路徑
csv_path="/home/eric/sample_data/iris.csv"

# ✅ 用 Container 路徑
csv_path="/data/sample_data/iris.csv"
```

### 2. ML 訓練用了暫存模式
```python
# ❌ 暫存模式無法訓練
upload_dataset(storage_mode="temporary")
submit_automl_job(...)  # 會失敗！

# ✅ 必須用永久模式
upload_dataset(storage_mode="permanent")
submit_automl_job(...)
```

### 3. 沒等待訓練完成
```python
# ❌ 直接取結果
submit_automl_job(...)
get_model_leaderboard(...)  # 會失敗！

# ✅ 先等待完成
result = submit_automl_job(...)
wait_for_job(result["job_id"])
get_model_leaderboard(...)
```

### 4. 忘記 user_id
```python
# 大多數操作都需要 user_id
upload_dataset(..., user_id="eric")
submit_automl_job(..., user_id="eric")
```

---

## 🔗 相關 Skills

| Skill | 用途 |
|-------|------|
| `mcp-quick-analysis` | 快速分析（跳過專案建立） |
| `ml-training-workflow` | ML 訓練細節 |
| `statistical-analysis-workflow` | 進階統計 |
| `data-cleaning-workflow` | 資料清理 |
| `result-delivery-workflow` | 結果交付 |
| `mcp-tools-reference` | 工具速查 |
