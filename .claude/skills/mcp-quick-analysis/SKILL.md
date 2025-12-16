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

## 🎯 工具選擇決策樹

```
使用者需求
    │
    ├─→ 「看看資料」「概覽」
    │       └─→ get_quick_stats + direct_preview_data
    │
    ├─→ 「分析這個資料」（有分組欄位）
    │       └─→ generate_tableone_directly
    │           ⚠️ 優先於 auto_analyze（更穩定）
    │
    ├─→ 「比較兩組」「治療效果」
    │       └─→ compare_groups
    │           • 自動選擇 t-test 或 Mann-Whitney
    │
    ├─→ 「相關性」「變數關係」
    │       └─→ analyze_correlations
    │           • 自動偵測數值欄位
    │
    ├─→ 「預測」「訓練模型」
    │       └─→ upload_dataset (storage_mode="temporary")
    │           └─→ train_and_wait
    │               └─→ get_model_leaderboard
    │
    ├─→ 「存活分析」「KM」「Cox」
    │       └─→ activate_group_4
    │           └─→ kaplan_meier_survival / cox_proportional_hazards
    │
    ├─→ 「傾向分數」「PSM」「IPTW」
    │       └─→ activate_group_1
    │           └─→ run_propensity_analysis
    │
    └─→ 「ROC」「AUC」「最佳閾值」
            └─→ activate_group_6
                └─→ compute_roc_curve / find_optimal_threshold
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

### 範例 1: 簡單分析

**使用者：** 幫我分析 iris.csv

**Agent 執行：**
```python
# Step 1: 路徑轉換
csv_path = "/data/sample_data/iris.csv"

# Step 2: 快速統計
get_quick_stats(csv_path=csv_path)

# Step 3: 無分組欄位 → 相關性分析
analyze_correlations(csv_path=csv_path, user_id="eric")
```

---

### 範例 2: 醫學研究

**使用者：** 分析 medical_study_200.csv，比較 treatment_group 對 bp_change 的效果

**Agent 執行：**
```python
csv_path = "/data/sample_data/medical_study_200.csv"

# Step 1: 快速統計
get_quick_stats(csv_path=csv_path)

# Step 2: Table One (有分組)
generate_tableone_directly(
    csv_path=csv_path,
    group_column="treatment_group",
    user_id="eric"
)

# Step 3: 組間比較
compare_groups(
    csv_path=csv_path,
    numeric_column="bp_change",
    group_column="treatment_group",
    user_id="eric"
)

# Step 4: 相關性
analyze_correlations(csv_path=csv_path, user_id="eric")
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

### auto_analyze 失敗

**錯誤：** `'<' not supported between instances of 'NoneType' and 'float'`

**原因：** 資料有缺失值

**解法：**
```python
# 改用更穩定的 generate_tableone_directly
generate_tableone_directly(csv_path=csv_path, group_column="...", user_id="eric")

# 或先處理缺失值
handle_missing_values(csv_path=csv_path, strategy="mean", output_path="...")
```

---

### Tool not found

**錯誤：** `mcp_automl_kaplan_meier_survival not found`

**原因：** 工具在其他 group，未啟用

**解法：**
```python
# 先啟用對應 group
activate_group_4()  # 存活分析
activate_group_1()  # 傾向分數
activate_group_6()  # ROC 分析
```

---

### 找不到檔案

**錯誤：** `File not found: /home/eric/.../xxx.csv`

**原因：** 用了 Host 路徑

**解法：** 轉為 Container 路徑 `/data/sample_data/xxx.csv`

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
- `mcp-tools-reference` - 工具速查
