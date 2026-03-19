---
name: mcp-data-analysis
description: Complete data analysis workflow including EDA, Table One, descriptive statistics, and correlation analysis using MCP AutoML tools. Use when analyzing CSV data, exploring datasets, generating summary statistics, or creating publication-ready Table One reports. Triggers: 分析資料, analyze data, EDA, 探索資料, 資料分析, describe data, 資料探索, 基本統計, summary statistics, Table One, 敘述統計, 看看資料, 快速分析, quick analysis, 分析一下, 幫我分析.
---

# MCP Data Analysis 技能 (資料分析流程)

## 描述
使用 MCP 工具進行完整資料分析的標準流程，支援自動路徑轉換和智能工具選擇。

## 觸發條件
- 「分析這個資料」「分析 {dataset}」
- 「EDA」「探索資料」「資料分析」
- 「看看這個資料」「資料概覽」
- 「快速分析」「分析一下」「幫我分析」

---

## 🔄 路徑自動轉換（重要！）

**黃金規則：MCP csv_path 永遠用 `/data/` 開頭**

| 使用者輸入 | 自動轉換為 |
|------------|-----------|
| `iris.csv` | `/data/sample_data/iris.csv` |
| `sample_data/medical.csv` | `/data/sample_data/medical.csv` |
| `projects/study1/data.csv` | `/data/projects/study1/data.csv` |
| `/home/eric/.../sample_data/xxx.csv` | `/data/sample_data/xxx.csv` |
| `/home/eric/.../projects/study1/data.csv` | `/data/projects/study1/data.csv` |
| `uploads/my_data.csv` | `/data/uploads/my_data.csv` |

**轉換邏輯：**
```python
def convert_to_container_path(user_path: str) -> str:
    """將任意路徑轉為 Container 路徑"""
    # 1. 已經是正確格式
    if user_path.startswith("/data/"):
        return user_path

    # 2. 只有檔名 → 預設 sample_data
    if "/" not in user_path:
        return f"/data/sample_data/{user_path}"

    # 3. 包含 projects → 保持專案結構
    if "projects" in user_path:
        return f"/data/projects/{user_path.split('projects/')[-1]}"

    # 4. 包含 sample_data
    if "sample_data" in user_path:
        return f"/data/sample_data/{user_path.split('sample_data/')[-1]}"

    # 5. 包含 uploads
    if "uploads" in user_path:
        return f"/data/uploads/{user_path.split('uploads/')[-1]}"

    # 6. Host 絕對路徑（無法判斷歸屬）→ 提示用戶確認
    if "/home/" in user_path:
        filename = os.path.basename(user_path)
        # 預設放 sample_data，但應提示用戶確認
        return f"/data/sample_data/{filename}"

    # 7. 預設
    return f"/data/sample_data/{user_path}"
```

**⚠️ 注意：** Host 路徑 `/home/eric/...` 如果沒有 `projects/` 或 `sample_data/` 關鍵字，會預設放到 `sample_data`，建議用戶明確指定目標位置。

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

# ✅ 更簡單：只提供檔名（自動轉換到 sample_data）
csv_path="iris.csv"  # → /data/sample_data/iris.csv

# ✅ 專案內檔案：保持專案結構
csv_path="projects/my_study/data/raw/patient_data.csv"
# → /data/projects/my_study/data/raw/patient_data.csv

# ✅ Host 專案路徑會自動識別
csv_path="/home/eric/workspace251204/projects/study1/data.csv"
# → /data/projects/study1/data.csv（保持專案結構）
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

---

## 📝 預設參數

```python
# 除非使用者指定，自動帶入：
DEFAULT_PARAMS = {
    "user_id": "eric",
    "storage_mode": "temporary",
    "method": "auto",
    "pval": True,
    "n_rows": 10,
}
```

---

## 🎯 工具選擇決策樹

```
使用者需求
    │
    ├─→ 「看看資料」「概覽」
    │       └─→ quick_preview / direct_preview_data
    │
    ├─→ 「分析這個資料」
    │       └─→ smart_analyze（推薦！整合 stats + tableone + correlations）
    │
    ├─→ 「比較兩組」「治療效果」
    │       └─→ compare_treatment_groups / compare_groups
    │
    ├─→ 「相關性」「變數關係」
    │       └─→ analyze_correlations
    │
    ├─→ 「Table One」「臨床基準表」
    │       └─→ generate_tableone_directly
    │
    ├─→ 「VIF」「共線性」
    │       └─→ check_multicollinearity
    │
    └─→ 「醫學研究完整分析」
            └─→ analyze_medical_study
```
