---
name: mcp-quick-analysis
description: Streamlined MCP analysis workflow with automatic path conversion and smart tool selection. Executes complete analysis pipeline with minimal user input. Use when user wants quick data analysis, one-click analysis, or automated workflow without specifying individual tools. Triggers: 快速分析, quick analysis, 分析一下, 看資料, 幫我分析, 一鍵分析, 自動分析, 跑一下.
---

# MCP Quick Analysis 技能 (快速分析)

## 描述
自動化的 MCP 分析流程，自動處理路徑轉換、工具選擇、結果彙整。

## 觸發條件
- 「快速分析」「分析一下」「幫我分析」
- 「一鍵分析」「自動分析」
- 「看資料」「跑一下」

---

## 🚀 使用方式

只需告訴我：
1. **資料在哪** - 檔名或路徑
2. **想知道什麼** - 比較、相關性、預測...

我會自動：
- ✅ 轉換路徑（Host → Container）
- ✅ 選擇正確工具
- ✅ 處理分組啟用
- ✅ 彙整結果報告

---

## 📋 標準執行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                   Quick Analysis Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Input] 使用者提供檔案                                          │
│     ↓                                                            │
│  [1] 路徑轉換 (自動)                                             │
│     • sample_data/xxx.csv → /data/sample_data/xxx.csv           │
│     • projects/yyy.csv → /data/projects/yyy.csv                 │
│     ↓                                                            │
│  [2] 快速預覽 (get_quick_stats)                                  │
│     • 行數、欄數、缺失值                                         │
│     • 數值 vs 類別欄位                                           │
│     ↓                                                            │
│  [3] 智能選擇分析工具                                            │
│     • 有分組 → generate_tableone_directly                       │
│     • 要比較 → compare_groups                                   │
│     • 看相關 → analyze_correlations                             │
│     • 要預測 → upload_dataset + train_and_wait                  │
│     ↓                                                            │
│  [4] 結果彙整                                                    │
│     • 建立 reports/analysis_YYYYMMDD.md                         │
│     • 列出所有 Result IDs                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 路徑自動轉換

**黃金規則：MCP csv_path 永遠用 `/data/` 開頭**

| 使用者輸入 | 自動轉換為 |
|------------|-----------|
| `iris.csv` | `/data/sample_data/iris.csv` |
| `sample_data/medical.csv` | `/data/sample_data/medical.csv` |
| `projects/study1/data.csv` | `/data/projects/study1/data.csv` |
| `/home/eric/.../xxx.csv` | `/data/sample_data/xxx.csv` |
| `uploads/my_data.csv` | `/data/uploads/my_data.csv` |

**轉換邏輯：**
```python
def convert_to_container_path(user_path: str) -> str:
    """將任意路徑轉為 Container 路徑"""
    # 1. 已經是正確格式
    if user_path.startswith("/data/"):
        return user_path
    
    # 2. 只有檔名
    if "/" not in user_path:
        return f"/data/sample_data/{user_path}"
    
    # 3. 包含 sample_data
    if "sample_data" in user_path:
        filename = user_path.split("sample_data/")[-1]
        return f"/data/sample_data/{filename}"
    
    # 4. 包含 projects
    if "projects" in user_path:
        project_path = user_path.split("projects/")[-1]
        return f"/data/projects/{project_path}"
    
    # 5. 包含 uploads
    if "uploads" in user_path:
        filename = user_path.split("uploads/")[-1]
        return f"/data/uploads/{filename}"
    
    # 6. Host 絕對路徑
    if "/home/" in user_path or "/workspace" in user_path:
        filename = os.path.basename(user_path)
        return f"/data/sample_data/{filename}"
    
    # 7. 預設
    return f"/data/sample_data/{user_path}"
```

---

## 🎯 工具選擇決策樹（51 個工具版本）

```
使用者需求
    │
    ├─→ 「看看資料」「概覽」
    │       └─→ quick_preview（自動路徑解析）
    │
    ├─→ 「分析這個資料」
    │       └─→ smart_analyze（推薦！）
    │           • 自動路徑解析
    │           • 整合 stats + tableone + correlations
    │           • 有分組 → 自動生成 Table One
    │
    ├─→ 「比較兩組」「治療效果」
    │       └─→ compare_treatment_groups（簡化版）
    │           或 compare_groups（完整版）
    │           • 自動選擇 t-test 或 Mann-Whitney
    │
    ├─→ 「相關性」「變數關係」
    │       └─→ analyze_correlations
    │           • 自動偵測數值欄位
    │
    ├─→ 「VIF」「共線性」
    │       └─→ check_multicollinearity
    │           • VIF > 5 表示有問題
    │
    ├─→ 「預測」「訓練模型」
    │       └─→ upload_dataset (storage_mode="temporary")
    │           └─→ train_and_wait
    │               └─→ get_model_leaderboard
    │
    ├─→ 「存活分析」「KM」「Cox」
    │       └─→ kaplan_meier_survival / cox_proportional_hazards
    │
    ├─→ 「傾向分數」「PSM」「IPTW」
    │       └─→ run_propensity_analysis
    │
    ├─→ 「ROC」「AUC」「最佳閾值」
    │       └─→ compute_roc_curve / find_optimal_threshold
    │
    ├─→ 「樣本數計算」「Power」
    │       └─→ power_ttest / power_proportion / power_anova
    │           • mode="sample_size" 或 "power"
    │
    └─→ 「醫學研究完整分析」
            └─→ analyze_medical_study
                • 一站式 RCT 分析
```

---

## 📝 預設參數

```python
# 除非使用者指定，自動帶入：
DEFAULT_PARAMS = {
    "user_id": "eric",
    "storage_mode": "temporary",  # 快速分析用
    "method": "auto",  # 讓工具自動選方法
    "pval": True,  # Table One 顯示 p 值
    "n_rows": 10,  # 預覽行數
}
```

---

## 📊 範例對話

### 範例 1: 簡單分析（使用整合工具）

**使用者：** 幫我分析 iris.csv

**Agent 執行：**
```python
# 一站式分析（推薦！）
smart_analyze(
    csv_path="iris.csv",  # 自動轉換路徑
    include_correlations=True
)
# 返回：quick_stats + correlations + summary
```

---

### 範例 2: 醫學研究（使用整合工具）

**使用者：** 分析 medical_study_200.csv，比較 treatment_group 對 bp_change 的效果

**Agent 執行：**
```python
# 方案 A: 完整研究分析（推薦！）
analyze_medical_study(
    csv_path="medical_study_200.csv",
    treatment_column="treatment_group",
    outcome_columns=["bp_change", "weight_change"]
)
# 返回：baseline table + treatment effects + correlations + report

# 方案 B: 分步分析
# Step 1: 帶分組的完整分析
smart_analyze(
    csv_path="medical_study_200.csv",
    group_column="treatment_group"
)
# 返回：quick_stats + tableone + correlations

# Step 2: 特定比較
compare_treatment_groups(
    csv_path="medical_study_200.csv",
    outcome_column="bp_change",
    treatment_column="treatment_group"
)
```

---

### 範例 3: 預測任務

**使用者：** 用 heart_disease.csv 預測 target

**Agent 執行：**
```python
csv_path = "/data/sample_data/heart_disease.csv"

# Step 1: 上傳（暫存）
result = upload_dataset(
    name="heart_quick",
    source_type="local",
    source_path=csv_path,
    storage_mode="temporary",
    user_id="eric"
)

# Step 2: 訓練
train_result = train_and_wait(
    dataset_id=result["dataset_id"],
    target_column="target",
    problem_type="binary",
    user_id="eric"
)

# Step 3: 查看結果
get_model_leaderboard(model_id=train_result["model_id"])
```

---

## ⚠️ 故障排除

### 工具選擇建議（51 個工具版本）

| 需求 | 推薦工具 | 備註 |
|------|----------|------|
| 「看資料」 | `quick_preview` | 自動路徑解析 |
| 「分析這個」 | `smart_analyze` | 一站式分析 |
| 「醫學研究」 | `analyze_medical_study` | RCT 完整流程 |
| 「比較兩組」 | `compare_treatment_groups` | 簡化版 |
| 「Table One」 | `generate_tableone_directly` | 出版級表格 |
| 「VIF/共線性」 | `check_multicollinearity` | 迴歸前診斷 |
| 「樣本數」 | `power_ttest` | mode="sample_size" |

---

### 找不到檔案

**錯誤：** `File not found: /home/eric/.../xxx.csv`

**原因：** 用了 Host 路徑

**解法：** 
- 使用整合工具（自動路徑解析）：`smart_analyze(csv_path="iris.csv")`
- 或手動轉換：`/data/sample_data/xxx.csv`

---

## 📋 結果彙整模板

每次分析完成後，建立報告：

```markdown
# 分析報告 - {dataset_name}

**時間**: {timestamp}
**資料**: {csv_path}

## 資料概覽
- 樣本數: {n_rows}
- 變數數: {n_cols}
- 缺失值: {missing_count}

## 分析結果

### Table One
{tableone_summary}
Result ID: `{tableone_result_id}`

### 組間比較
{compare_summary}
Result ID: `{compare_result_id}`

### 相關性
{correlation_summary}
Result ID: `{correlation_result_id}`

## Result IDs 彙整
| 分析 | Result ID |
|------|-----------|
| Table One | {tableone_result_id} |
| Compare | {compare_result_id} |
| Correlation | {correlation_result_id} |
```

---

## 🔗 相關 Skills

- `data-analysis-workflow` - 完整分析流程（含詳細說明）
- `ml-training-workflow` - ML 訓練專用
- `statistical-analysis-workflow` - 進階統計
- `mcp-tools-reference` - 51 個工具速查
