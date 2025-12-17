---
name: mcp-result-delivery
description: Result delivery workflow for retrieving analysis results, downloading files from MinIO, and sharing reports with users. Use when user wants to download results, export reports, get analysis outputs, or share data files. Triggers: 下載結果, 取得報告, 傳檔案, share results, download, 輸出, export, 結果在哪, where is result, 報告, report, 圖表, visualization.
---

# Result Delivery Workflow 技能 (結果交付流程)

## 描述
管理分析結果的儲存、查詢和交付給使用者。

## 觸發條件
- 「下載結果」「取得報告」
- 「傳檔案給我」「share results」
- 「之前的分析結果」「歷史記錄」

---

## 🎯 結果交付架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Result Storage Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   分析工具執行                                                        │
│        ↓                                                            │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                     Result Storage                          │   │
│   │                                                             │   │
│   │   ┌─────────────┐          ┌─────────────┐                 │   │
│   │   │   Redis     │          │   MinIO     │                 │   │
│   │   │  (7 天快取)  │          │  (永久儲存) │                 │   │
│   │   │             │          │             │                 │   │
│   │   │ stats:result│          │ automl-results/               │   │
│   │   │ :{result_id}│          │ {user}/{type}/                │   │
│   │   └─────────────┘          │ {timestamp}_{id}.json         │   │
│   │                            └─────────────┘                 │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│   回傳給 Agent：                                                      │
│   • result_id: stat_tableone_abc12345                               │
│   • result_path: automl-results/eric/tableone/20251216_xxx.json     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 結果類型

### 支援自動儲存的工具

| 工具 | 分析類型 | 儲存位置 |
|------|----------|----------|
| `compare_groups` | compare_groups | ✅ Redis + MinIO |
| `analyze_correlations` | correlation | ✅ Redis + MinIO |
| `generate_tableone_directly` | tableone | ✅ Redis + MinIO |
| `auto_analyze` | auto_analyze | ✅ Job 系統 |
| `kaplan_meier_survival` | survival | ✅ Job 系統 |
| `cox_proportional_hazards` | cox | ✅ Job 系統 |
| `compute_roc_curve` | roc | ✅ Redis + MinIO |

### 儲存格式

```json
{
  "metadata": {
    "result_id": "stat_tableone_abc12345",
    "analysis_type": "tableone",
    "user_id": "eric",
    "created_at": "2025-12-16T10:30:00"
  },
  "result": {
    // 實際分析結果...
  }
}
```

---

## 📋 查詢歷史結果

### Step 1: 列出使用者的結果

```python
mcp_automl_list_analysis_results(
    user_id="eric",
    analysis_type="tableone",  # 可選：過濾類型
    limit=20
)
```

**輸出：**
```json
{
  "status": "success",
  "user_id": "eric",
  "count": 5,
  "keys": [
    "stats:result:stat_tableone_abc12345",
    "stats:result:stat_tableone_def67890",
    ...
  ]
}
```

### Step 2: 取得特定結果

```python
mcp_automl_get_analysis_result(
    result_id="stat_tableone_abc12345"
)
```

**輸出：**
```json
{
  "status": "success",
  "result_id": "stat_tableone_abc12345",
  "metadata": {...},
  "result": {...}
}
```

---

## 📥 從 MinIO 下載檔案

### 直接使用 Stats Service API

```
GET http://localhost:8003/storage/minio/download?bucket=automl-results&path=eric/tableone/xxx.json
```

### 列出 MinIO 物件

```
GET http://localhost:8003/storage/minio/list?bucket=automl-results&prefix=eric/
```

---

## 🖼️ 視覺化結果

### 目前狀態

視覺化功能回傳 **figure_data**（座標資料），而非圖片檔案。

### 支援圖表資料的工具

| 工具 | 圖表類型 | 回傳欄位 |
|------|----------|----------|
| `compute_roc_curve` | ROC 曲線 | `figure_data.curve_points` |
| `kaplan_meier_survival` | KM 曲線 | `survival_curve` |
| `analyze_correlations` | 熱力圖 | `heatmap_data` |
| `analyze_calibration` | 校準曲線 | `reliability_diagram_data` |
| `ttest_sensitivity_analysis` | Power 曲線 | `power_curve_data` |

### 圖表資料範例

```json
{
  "figure_data": {
    "curve_points": [
      {"fpr": 0.0, "tpr": 0.0},
      {"fpr": 0.1, "tpr": 0.5},
      ...
    ],
    "auc": 0.85,
    "optimal_threshold": {"fpr": 0.15, "tpr": 0.82}
  }
}
```

### Agent 如何呈現圖表

```markdown
User: "畫出 ROC 曲線"

Agent:
1. 執行 compute_roc_curve 取得 figure_data
2. 在回應中用 Markdown 說明數據：

"📊 ROC 分析結果：
- AUC = 0.85 (95% CI: 0.80-0.90)
- 最佳閾值 = 0.45 (Youden's J)
- 敏感度 = 82%, 特異度 = 85%

如需繪製圖表，可用以下 Python 程式碼：

\`\`\`python
import matplotlib.pyplot as plt
fpr = [0.0, 0.1, 0.2, ...]  # from figure_data
tpr = [0.0, 0.5, 0.7, ...]
plt.plot(fpr, tpr)
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title(f'ROC Curve (AUC = 0.85)')
plt.show()
\`\`\`
"
```

---

## 📤 交付結果給使用者

### 方式 1：直接在對話中呈現

```markdown
User: "分析結果如何？"

Agent:
"✅ Table One 分析完成

| 變數 | Group A (n=100) | Group B (n=150) | p-value |
|------|-----------------|-----------------|---------|
| Age | 45.2 ± 12.3 | 48.1 ± 11.8 | 0.032 |
| Sex (M) | 60 (60%) | 85 (57%) | 0.58 |

📎 結果已儲存：
- Result ID: `stat_tableone_abc12345`
- MinIO 路徑: `automl-results/eric/tableone/20251216_xxx.json`

取得完整結果：
\`\`\`python
result = get_analysis_result('stat_tableone_abc12345')
\`\`\`
"
```

### 方式 2：提供下載連結

```markdown
Agent:
"📁 分析結果已儲存：

| 項目 | 路徑 |
|------|------|
| JSON | `automl-results/eric/tableone/20251216_xxx.json` |

📥 下載方式：
1. 透過 MinIO Console: http://localhost:9001
2. 透過 API: GET /storage/minio/download?bucket=automl-results&path=...
"
```

### 方式 3：匯出為特定格式

```markdown
User: "我需要 CSV 格式"

Agent:
"目前系統儲存為 JSON 格式。我可以幫你轉換：

\`\`\`python
import pandas as pd
import json

# 載入 JSON 結果
with open('result.json') as f:
    data = json.load(f)

# 轉為 DataFrame
df = pd.DataFrame(data['result']['table'])

# 儲存為 CSV
df.to_csv('tableone_result.csv', index=False)
\`\`\`

或者我可以直接在這裡以表格形式呈現，你可以複製到 Excel。
"
```

---

## 🗂️ 專案管理

### 建議的目錄結構

使用者可以用 `/data/projects/` 目錄組織專案：

```
/data/projects/
├── my_study_2025/
│   ├── data/
│   │   ├── raw/              # 原始資料
│   │   └── processed/        # 清理後資料
│   ├── analysis/
│   │   ├── descriptive/      # 描述性統計
│   │   ├── survival/         # 存活分析
│   │   └── models/           # ML 模型
│   └── reports/              # 最終報告
│
└── another_project/
    └── ...
```

### 清理後資料輸出

資料清理工具支援 `output_path`：

```python
mcp_automl_handle_missing_values(
    csv_path="/data/sample_data/titanic.csv",
    strategy="median",
    output_path="/data/projects/my_study/data/processed/titanic_cleaned.csv"
)
```

---

## ⏳ 結果保留期限

| 儲存位置 | 保留期限 | 用途 |
|----------|----------|------|
| Redis | **7 天** | 快速存取、最近分析 |
| MinIO | **永久** | 審計追蹤、重現性 |

### 超過 7 天後取得結果

如果 Redis 結果已過期，但 MinIO 仍有：

```python
# 方式 1：透過 MinIO 路徑下載
GET /storage/minio/download?bucket=automl-results&path=eric/tableone/xxx.json

# 方式 2：列出使用者的所有 MinIO 結果
GET /storage/minio/list?bucket=automl-results&prefix=eric/
```

---

## 🔄 完整交付流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Result Delivery Workflow                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   1. 使用者要求分析                                                   │
│      「分析這個資料的存活情況」                                        │
│           ↓                                                         │
│   2. Agent 執行分析工具                                               │
│      kaplan_meier_survival(..., save_result=True)                   │
│           ↓                                                         │
│   3. 結果自動儲存                                                     │
│      • Redis: stats:result:stat_survival_xxx                        │
│      • MinIO: automl-results/eric/survival/xxx.json                 │
│           ↓                                                         │
│   4. Agent 呈現結果                                                   │
│      • 主要指標摘要                                                   │
│      • 表格/圖表說明                                                  │
│      • 提供 result_id 和 path                                        │
│           ↓                                                         │
│   5. 使用者要求詳細資料                                               │
│      「給我完整的數據」                                               │
│           ↓                                                         │
│   6. Agent 取得完整結果                                               │
│      get_analysis_result(result_id)                                 │
│           ↓                                                         │
│   7. 提供下載/匯出選項                                               │
│      • JSON 原始資料                                                 │
│      • 轉換程式碼                                                    │
│      • MinIO 下載連結                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💡 最佳實踐

### 1. 永遠提供 result_id

每次分析後，告訴使用者 `result_id`，方便日後查詢。

### 2. 摘要優先，細節隨需

先呈現重要指標，使用者需要時再提供完整數據。

### 3. 建議專案目錄

幫使用者建立組織良好的專案結構。

### 4. 提供多種格式選項

使用者可能需要 JSON、CSV、或直接複製的表格。

### 5. 說明保留期限

告知 Redis 7 天限制，建議重要結果下載備份。
