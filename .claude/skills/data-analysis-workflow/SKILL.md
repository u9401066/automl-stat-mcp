---
name: data-analysis-workflow
description: Complete data analysis workflow including EDA, Table One, descriptive statistics, and correlation analysis using MCP AutoML tools. Use when analyzing CSV data, exploring datasets, generating summary statistics, or creating publication-ready Table One reports. Triggers: 分析資料, analyze data, EDA, 探索資料, 資料分析, describe data, 資料探索, 基本統計, summary statistics, Table One, 敘述統計, 看看資料.
---

# Data Analysis Workflow 技能 (資料分析流程)

## 描述
使用 MCP 工具進行完整資料分析的標準流程。

## 觸發條件
- 「分析這個資料」「分析 {dataset}」
- 「EDA」「探索資料」「資料分析」
- 「看看這個資料」「資料概覽」

---

## 🎯 分析流程總覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Analysis Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   [1] 確認資料        →  list_available_files / direct_preview_data │
│         ↓                                                           │
│   [2] 快速統計        →  get_quick_stats / get_column_info          │
│         ↓                                                           │
│   [3] 深入分析        →  auto_analyze / generate_tableone_directly  │
│         ↓                                                           │
│   [4] 特定分析        →  compare_groups / analyze_correlations      │
│         ↓                                                           │
│   [5] 結果儲存        →  結果自動存到 Redis + MinIO                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Step 1: 確認資料來源

### 1.1 列出可用檔案

```python
# 使用 MCP 工具列出檔案
mcp_automl_list_available_files(
    directory="/data/sample_data"  # 或 "/data/projects"
)
```

**常用資料目錄：**
| 路徑 | 說明 |
|------|------|
| `/data/sample_data/` | 範例資料集 |
| `/data/projects/{project}/` | 使用者專案資料 |

### 1.2 預覽資料

```python
# 預覽前幾行
mcp_automl_direct_preview_data(
    csv_path="/data/sample_data/iris.csv",
    n_rows=10
)
```

### 1.3 取得欄位資訊

```python
# 取得欄位類型、缺失值等資訊
mcp_automl_get_column_info(
    csv_path="/data/sample_data/heart_disease.csv"
)
```

---

## 📋 Step 2: 快速統計

### 2.1 快速統計摘要

```python
mcp_automl_get_quick_stats(
    csv_path="/data/sample_data/titanic.csv"
)
```

**輸出包含：**
- 總筆數、欄位數
- 各欄位類型
- 缺失值統計
- 數值欄位基本統計

### 2.2 檢查缺失值

```python
mcp_automl_analyze_missing_values(
    csv_path="/data/sample_data/titanic.csv"
)
```

---

## 📋 Step 3: 深入分析

### 3.1 智能自動分析（推薦！）

```python
# 系統自動判斷資料類型並執行適合的分析
mcp_automl_auto_analyze(
    csv_path="/data/sample_data/heart_disease.csv",
    target_column="target",  # 可選：指定目標欄位
    user_id="eric"
)
```

### 3.2 生成 Table One（臨床研究必備）

```python
mcp_automl_generate_tableone_directly(
    csv_path="/data/sample_data/medical_study_200.csv",
    group_column="treatment",     # 分組欄位
    columns=["age", "gender", "bmi", "outcome"],  # 可選
    categorical=["gender"],       # 類別變數
    pval=True,                    # 計算 p-value
    user_id="eric"
)
```

### 3.3 快速 EDA 報告

```python
mcp_automl_run_quick_eda(
    dataset_id="your-dataset-id",  # 需要先註冊資料集
    user_id="eric"
)
```

---

## 📋 Step 4: 特定分析

### 4.1 組間比較

```python
# 比較兩組或多組的數值差異
mcp_automl_compare_groups(
    csv_path="/data/sample_data/heart_disease.csv",
    numeric_column="age",        # 要比較的數值欄位
    group_column="target",       # 分組欄位
    save_result=True,
    user_id="eric"
)
```

**會自動選擇統計方法：**
- 2 組 + 常態分佈 → t-test
- 2 組 + 非常態 → Mann-Whitney U
- 3+ 組 + 常態 → ANOVA
- 3+ 組 + 非常態 → Kruskal-Wallis

### 4.2 相關性分析

```python
mcp_automl_analyze_correlations(
    csv_path="/data/sample_data/diabetes.csv",
    columns=["age", "bmi", "blood_pressure", "glucose"],  # 可選
    method="pearson",   # pearson, spearman, kendall
    save_result=True,
    user_id="eric"
)
```

### 4.3 多重共線性檢查 (VIF)

```python
mcp_automl_check_multicollinearity(
    csv_path="/data/sample_data/boston.csv",
    columns=["rm", "lstat", "ptratio", "tax"],  # 可選
    vif_threshold=5.0   # VIF > 5 視為有問題
)
```

---

## 📋 Step 5: 結果處理

### 5.1 結果會自動儲存

支援結果儲存的工具會返回：

```json
{
  "result_id": "stat_compare_groups_abc12345",
  "result_path": "automl-results/eric/compare_groups/20251216_...",
  "summary": { ... },
  "details": { ... }
}
```

### 5.2 列出已儲存的結果

```python
mcp_automl_list_analysis_results(
    user_id="eric",
    analysis_type="compare_groups"  # 可選
)
```

### 5.3 取回之前的結果

```python
mcp_automl_get_analysis_result(
    result_id="stat_compare_groups_abc12345"
)
```

---

## 🎯 常見分析場景

### 場景 1：臨床研究基準分析

```
User: "分析 medical_study_200.csv，按 treatment 分組"

Agent 執行順序：
1. direct_preview_data → 預覽資料結構
2. get_column_info → 確認欄位類型
3. generate_tableone_directly → 生成 Table 1
```

### 場景 2：探索性資料分析

```
User: "探索 heart_disease.csv"

Agent 執行順序：
1. get_quick_stats → 基本統計
2. analyze_missing_values → 缺失值分析
3. analyze_correlations → 相關性分析
4. auto_analyze → 智能分析
```

### 場景 3：ML 前置分析

```
User: "準備用 titanic.csv 做 ML，先看看資料"

Agent 執行順序：
1. get_column_info → 欄位資訊
2. analyze_missing_values → 缺失值
3. check_multicollinearity → VIF 檢查
4. compare_groups(target) → 目標變數分布
```

---

## 📊 可用範例資料集

| 資料集 | 路徑 | 適合分析 |
|--------|------|----------|
| iris.csv | `/data/sample_data/iris.csv` | 分類、聚類 |
| titanic.csv | `/data/sample_data/titanic.csv` | 二元分類 |
| heart_disease.csv | `/data/sample_data/heart_disease.csv` | 二元分類、Table One |
| diabetes.csv | `/data/sample_data/diabetes.csv` | 迴歸、相關性 |
| breast_cancer.csv | `/data/sample_data/breast_cancer.csv` | 二元分類 |
| medical_study_200.csv | `/data/sample_data/medical_study_200.csv` | Table One、組間比較 |
| rossi_recidivism.csv | `/data/sample_data/rossi_recidivism.csv` | 存活分析 |
| stanford_heart.csv | `/data/sample_data/stanford_heart.csv` | 存活分析 |

---

## ⚠️ 常見錯誤

### 路徑錯誤
```python
# ❌ 錯誤：使用 Host 路徑
csv_path="/home/eric/workspace251204/sample_data/iris.csv"

# ✅ 正確：使用 Container 路徑
csv_path="/data/sample_data/iris.csv"
```

### 欄位名稱錯誤
```python
# 先確認欄位名稱
info = mcp_automl_get_column_info(csv_path="...")
# 再使用正確的欄位名稱
```

### 忘記指定 user_id
```python
# 需要儲存結果時，必須提供 user_id
mcp_automl_compare_groups(
    ...,
    save_result=True,
    user_id="eric"  # 必要！
)
```
