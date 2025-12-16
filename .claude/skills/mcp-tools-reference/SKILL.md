---
name: mcp-tools-reference
description: Quick reference guide for all 51 AutoML MCP tools organized by category. Use when looking up tool names, checking available MCP functions, or understanding tool parameters. Triggers: MCP 工具, 有什麼工具, 工具清單, tools reference, 工具列表, available tools, 怎麼用, how to use, tool help, 工具說明.
---

# MCP Tools Reference 技能 (MCP 工具速查)

## 描述
所有 51 個 AutoML MCP 工具的快速參照，幫助選擇正確的工具。

## 觸發條件
- 「有什麼工具」「工具清單」
- 「MCP 工具」「tools reference」

---

## 📊 工具總覽 (51 個公開)

| 類別 | 數量 | 主要用途 |
|------|------|----------|
| 🎯 整合分析 | 4 | 一站式分析（推薦入口） |
| 🧹 資料清理 | 7 | 缺失值、編碼、篩選 |
| 📁 資料管理 | 5 | 上傳、列出、刪除資料集 |
| 📈 基礎統計 | 6 | 統計摘要、Table One、相關性 |
| 🔬 存活分析 | 2 | KM 曲線、Cox 迴歸 |
| 🎯 傾向分數 | 2 | PSM、治療效果 |
| 📊 ROC 分析 | 4 | ROC 曲線、閾值優化 |
| 📐 Power 分析 | 5 | 樣本數、檢定力（統一版） |
| 🤖 ML 訓練 | 2 | AutoML 訓練 |
| 📋 Job 管理 | 6 | 狀態、結果、取消 |
| 🗂️ 模型管理 | 4 | 模型操作、預測 |
| 🔄 智慧工作流 | 2 | 資料驗證與清理 |
| 📥 結果查詢 | 2 | 分析結果管理 |
| **總計** | **51** | |

---

## 🎯 整合分析工具（推薦入口）

這 4 個工具是**最常用的入口點**，整合多個功能於一身：

| 工具 | 用途 | 何時使用 |
|------|------|----------|
| `smart_analyze` | 一站式資料分析 | 「分析這個資料」「看看資料」 |
| `analyze_medical_study` | 醫學研究分析 | 「分析治療效果」「RCT 分析」 |
| `quick_preview` | 快速資料預覽 | 「預覽」「有什麼欄位」 |
| `compare_treatment_groups` | 組間比較 | 「比較兩組」「治療對照」 |

### smart_analyze（推薦！）
```python
smart_analyze(
    csv_path="iris.csv",           # 自動路徑解析！
    group_column="species",        # 可選：分組欄位
    include_correlations=True      # 可選：包含相關性
)
# 返回：quick_stats + tableone + correlations
```

---

## 🧹 資料清理工具 (7)

| 工具 | 用途 | 關鍵參數 |
|------|------|----------|
| `handle_missing_values` | 處理缺失值 | `strategy`: mean/median/mode/drop |
| `remove_columns` | 移除欄位 | `columns`: List[str] |
| `rename_columns` | 重新命名 | `mapping`: {"old": "new"} |
| `filter_rows` | 篩選資料 | `condition`: "age > 30" |
| `encode_categorical` | 類別編碼 | `method`: onehot/label |
| `convert_to_binary` | 轉換 0/1 | `mapping`: {"yes": 1, "no": 0} |
| `get_column_info` | 欄位資訊 | 顯示類型、缺失、唯一值 |

---

## 📁 資料管理工具 (5)

| 工具 | 用途 | 說明 |
|------|------|------|
| `list_available_files` | 列出檔案 | `/data/sample_data/` 下的 CSV |
| `upload_dataset` | 上傳資料集 | 上傳到 MinIO |
| `register_dataset` | 註冊資料集 | 從 MinIO 路徑註冊 |
| `list_datasets` | 列出資料集 | 已註冊的資料集 |
| `delete_dataset` | 刪除資料集 | 從 MinIO 刪除 |

---

## 📈 基礎統計工具 (6)

| 工具 | 用途 | 輸出 |
|------|------|------|
| `get_quick_stats` | 快速統計 | 行數、欄位、缺失值、基本統計 |
| `generate_tableone_directly` | 生成 Table 1 | 出版級基線特徵表 |
| `compare_groups` | 組間比較 | t-test / ANOVA / Mann-Whitney |
| `analyze_correlations` | 相關性分析 | Pearson / Spearman 矩陣 |
| `analyze_missing_values` | 缺失值分析 | MCAR/MAR/MNAR 判斷 |
| `check_multicollinearity` | VIF 分析 | 多重共線性檢測 |

### generate_tableone_directly
```python
generate_tableone_directly(
    csv_path="/data/sample_data/titanic.csv",
    groupby="Survived",
    categorical=["Sex", "Pclass"],
    pval=True
)
```

### check_multicollinearity
```python
check_multicollinearity(
    csv_path="/data/sample_data/data.csv",
    columns=["age", "income", "education"],
    vif_threshold=5.0  # VIF > 5 表示有共線性問題
)
```

---

## 🔬 存活分析工具 (2)

| 工具 | 用途 | 輸出 |
|------|------|------|
| `kaplan_meier_survival` | KM 曲線 | 存活曲線 + Log-rank test |
| `cox_proportional_hazards` | Cox 迴歸 | HR + CI + p-value |

```python
kaplan_meier_survival(
    csv_path="/data/sample_data/rossi_recidivism.csv",
    time_col="week",
    event_col="arrest",
    group_col="fin"
)
```

---

## 🎯 傾向分數工具 (2)

| 工具 | 用途 | 說明 |
|------|------|------|
| `run_propensity_analysis` | 完整 PSM 分析 | 一站式：估計 + 配對 + 平衡檢查 |
| `estimate_treatment_effect` | 治療效果估計 | ATE/ATT/IPTW |

```python
run_propensity_analysis(
    csv_path="/data/sample_data/data.csv",
    treatment_col="treatment",
    outcome_col="outcome",
    covariates=["age", "sex", "baseline"]
)
```

---

## 📊 ROC 分析工具 (4)

| 工具 | 用途 | 輸出 |
|------|------|------|
| `compute_roc_curve` | 計算 ROC | AUC + CI + 曲線 |
| `compare_roc_curves` | DeLong 比較 | 兩模型 AUC 差異檢定 |
| `find_optimal_threshold` | 最佳閾值 | Youden / Cost-based |
| `full_classifier_evaluation` | 完整評估 | ROC + 校準 + 分類報告 |

```python
full_classifier_evaluation(
    csv_path="/data/sample_data/data.csv",
    y_true_col="actual",
    y_score_col="predicted_prob"
)
```

---

## 📐 Power 分析工具 (5) ⭐ 統一版

原本 18 個工具現在整合為 5 個，每個支援多種 `mode`：

| 工具 | Mode 選項 | 用途 |
|------|-----------|------|
| `power_ttest` | sample_size / power / sensitivity / effect_size | T 檢定 |
| `power_proportion` | sample_size / power / sensitivity | 比例檢定 |
| `power_anova` | sample_size / power / effect_size | ANOVA |
| `power_chisquare` | sample_size / power / effect_size | 卡方檢定 |
| `power_survival` | sample_size / power / events / from_medians | 存活分析 |

### 範例
```python
# 計算樣本數
power_ttest(effect_size=0.5, mode="sample_size", power=0.80)

# 計算檢定力
power_ttest(effect_size=0.5, mode="power", n1=50)

# 敏感度分析
power_ttest(effect_size=0.5, mode="sensitivity")

# 計算效果量
power_ttest(mode="effect_size", mean1=100, mean2=115, pooled_sd=30)
```

---

## 🤖 ML 訓練工具 (2)

| 工具 | 用途 | 說明 |
|------|------|------|
| `submit_automl_job` | 提交訓練 | 非同步，返回 job_id |
| `train_and_wait` | 訓練並等待 | 同步，直接返回結果 |

```python
# 簡單版（推薦）
train_and_wait(
    dataset_id="abc123",
    target_column="label",
    problem_type="binary",
    user_id="eric",
    time_limit=300
)
```

---

## 📋 Job 管理工具 (6)

| 工具 | 用途 |
|------|------|
| `get_job_status` | 查詢 AutoML job 狀態 |
| `list_jobs` | 列出所有 jobs |
| `cancel_job` | 取消 job |
| `get_stats_job_status` | 查詢統計 job 狀態 |
| `get_stats_job_result` | 取得統計 job 結果 |
| `list_stats_jobs` | 列出統計 jobs |

---

## 🗂️ 模型管理工具 (4)

| 工具 | 用途 |
|------|------|
| `list_models` | 列出所有模型 |
| `get_model_leaderboard` | 模型排行榜 |
| `predict` | 使用模型預測 |
| `delete_model` | 刪除模型 |

---

## 🔄 智慧工作流工具 (2)

| 工具 | 用途 | 說明 |
|------|------|------|
| `start_data_analysis` | 開始分析 | 資料驗證 + 問題偵測 |
| `execute_analysis_ticket` | 執行分析 | 資料清理 + 持久化選項 |

這兩個工具提供**兩階段工作流**：
1. `start_data_analysis` 檢測資料問題（PII、缺失值、異常值）
2. 使用者決定如何處理
3. `execute_analysis_ticket` 執行清理並分析

---

## 📥 結果查詢工具 (2)

| 工具 | 用途 |
|------|------|
| `list_analysis_results` | 列出分析結果 |
| `get_analysis_result` | 取得特定結果 |

---

## 🎯 常用工作流

### 快速探索資料
```
quick_preview → smart_analyze
```

### 完整資料分析
```
list_available_files → quick_preview → smart_analyze → generate_tableone_directly
```

### ML 訓練流程
```
upload_dataset → train_and_wait → get_model_leaderboard → predict
```

### 存活分析流程
```
kaplan_meier_survival → cox_proportional_hazards
```

### 傾向分數分析
```
run_propensity_analysis → estimate_treatment_effect
```

### Power 分析流程
```
power_ttest(mode="effect_size") → power_ttest(mode="sample_size")
```

---

## ⚠️ 重要提醒

### 路徑規則
- ✅ 整合工具自動解析：`smart_analyze(csv_path="iris.csv")`
- ✅ Container 路徑：`/data/sample_data/iris.csv`
- ❌ 不要用 Host 路徑：`/home/eric/...`

### user_id
- 預設使用 `"eric"`
- 用於資源隔離

### 工具選擇建議
| 需求 | 推薦工具 |
|------|----------|
| 「看看資料」 | `quick_preview` |
| 「分析這個」 | `smart_analyze` |
| 「比較兩組」 | `compare_groups` |
| 「Table One」 | `generate_tableone_directly` |
| 「訓練模型」 | `train_and_wait` |
| 「存活分析」 | `kaplan_meier_survival` |
| 「樣本數計算」 | `power_*` 工具 |
| 「VIF/共線性」 | `check_multicollinearity` |

---

## 🔧 故障排除指南

### 常見錯誤與解法

| 錯誤訊息 | 原因 | 解法 |
|----------|------|------|
| `File not found` | 路徑錯誤 | 確認用 `/data/sample_data/` 開頭 |
| `'<' not supported between NaN` | 資料有缺失值 | 先用 `handle_missing_values` 處理 |
| `Column not found` | 欄位名錯誤 | 用 `quick_preview` 確認欄位名 |
| `Invalid column type` | 類型不符 | 數值分析不能用文字欄位 |
| `Job timeout` | 任務超時 | 減少資料量或增加 `time_limit` |
| `Service unavailable` | 服務未啟動 | 執行 `docker compose up -d` |

### 路徑轉換規則

```
使用者輸入                      → 正確路徑
─────────────────────────────────────────────────
iris.csv                       → /data/sample_data/iris.csv
sample_data/iris.csv           → /data/sample_data/iris.csv
/data/sample_data/iris.csv     → /data/sample_data/iris.csv (不變)
/home/eric/.../sample_data/x.csv → /data/sample_data/x.csv
```

### 資料類型問題

```python
# ❌ 常見錯誤：對類別欄位做數值分析
analyze_correlations(csv_path="data.csv", columns=["name", "age"])

# ✅ 正確：只選數值欄位
analyze_correlations(csv_path="data.csv", columns=["age", "income"])

# 💡 用 quick_preview 先確認欄位類型
quick_preview(csv_path="data.csv")
```

### 缺失值處理

```python
# 步驟 1：檢查缺失情況
analyze_missing_values(csv_path="data.csv")

# 步驟 2：處理缺失值
handle_missing_values(
    csv_path="data.csv",
    strategy="mean",  # 或 "median", "mode", "drop"
    columns=["age", "income"]
)

# 步驟 3：再執行分析
smart_analyze(csv_path="processed/data_cleaned.csv")
```

### 服務狀態檢查

```bash
# 檢查服務
docker compose ps

# 查看日誌
docker compose logs -f stats-service

# 重啟服務
docker compose restart stats-service
```

### 測試資料流

```bash
# 執行資料流測試
./scripts/run_tests.sh dataflow

# 執行所有測試
./scripts/run_tests.sh all

# 快速煙霧測試
./scripts/run_tests.sh quick
```

---

## 📊 測試資料集

| 資料集 | 檔案 | 筆數 | 用途 |
|--------|------|------|------|
| Iris | `iris.csv` | 150 | 多類別分類 |
| Heart Disease | `heart_disease.csv` | 297 | 二元分類 |
| Titanic | `titanic.csv` | 891 | 有缺失值 |
| Rossi | `rossi_recidivism.csv` | 432 | 存活分析 |
| Breast Cancer | `breast_cancer.csv` | 569 | 二元分類 |
| Diabetes | `diabetes.csv` | 442 | 迴歸 |
| Medical Study | `medical_study_200.csv` | 200 | 治療效果
