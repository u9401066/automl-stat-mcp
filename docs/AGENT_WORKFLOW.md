# Agent 工作流程設計文件

## 🎯 核心原則

**Agent 只負責四件事：**

1. **傳入檔案路徑** - 告訴系統資料在哪裡
2. **建立工單** - 設定要做什麼任務（含參數）
3. **查詢狀態** - 檢查工單執行進度
4. **取得結果連結** - 獲取輸出檔案（模型/報告/圖片）

**系統內部負責所有其他事情：**
- 資料讀取、驗證、清理、轉換
- 模型訓練、調參、評估
- 統計計算、假設檢定
- 報告生成、圖表繪製
- 檔案儲存、版本管理

---

## 📋 精簡後的 MCP 工具清單

### 必要工具（共 12 個）

| 工具 | 用途 | 輸入 | 輸出 |
|------|------|------|------|
| **檔案操作** |
| `list_available_files` | 列出可用檔案 | directory | files[] |
| `get_upload_help` | 上傳說明 | - | instructions |
| **工單建立** |
| `submit_ml_job` | 建立 ML 訓練工單 | file_path, target, settings | job_id |
| `submit_stats_job` | 建立統計分析工單 | file_path, analysis_type, settings | job_id |
| **狀態查詢** |
| `get_job_status` | 查詢工單狀態 | job_id | status, progress, message |
| `list_jobs` | 列出所有工單 | user_id | jobs[] |
| **結果取得** |
| `get_job_result` | 取得工單結果 | job_id | result_url, metrics, artifacts |
| `get_model_info` | 取得模型資訊 | model_id | leaderboard, feature_importance |
| **預測** |
| `submit_predict_job` | 建立預測工單 | model_id, file_path | job_id |
| **輔助** |
| `health_check` | 服務健康檢查 | - | status |
| `list_analysis_types` | 列出可用分析類型 | - | types[] |
| `get_job_help` | 工單建立說明 | job_type | parameters, examples |

---

## 🔄 標準工作流程

### ML 訓練流程

```
User: "用 titanic.csv 預測 survived"

Agent 執行:
1. list_available_files("/data/sample_data")
   → 確認 titanic.csv 存在

2. submit_ml_job(
     file_path="/data/sample_data/titanic.csv",
     target_column="survived",
     problem_type="binary",        # 可選，系統會自動判斷
     time_limit=300,               # 可選
     presets="medium_quality"      # 可選
   )
   → job_id: "ml-abc123"

3. get_job_status(job_id="ml-abc123")
   → status: "running", progress: 45%

4. get_job_status(job_id="ml-abc123")  # 輪詢直到完成
   → status: "completed", model_id: "model-xyz789"

5. get_job_result(job_id="ml-abc123")
   → {
       model_id: "model-xyz789",
       best_model: "WeightedEnsemble_L2",
       metrics: { accuracy: 0.82, roc_auc: 0.87 },
       leaderboard_url: "http://.../leaderboard.json",
       feature_importance_url: "http://.../importance.png"
     }

Agent 回報:
"訓練完成！最佳模型 WeightedEnsemble_L2 達到 87% AUC。"
```

### 統計分析流程

```
User: "分析 heart_disease.csv，按 target 分組"

Agent 執行:
1. submit_stats_job(
     file_path="/data/sample_data/heart_disease.csv",
     analysis_type="tableone",
     settings={
       groupby: "target",
       pval: true
     }
   )
   → job_id: "stats-def456"

2. get_job_status(job_id="stats-def456")
   → status: "completed"

3. get_job_result(job_id="stats-def456")
   → {
       table_url: "http://.../tableone.html",
       summary: { n: 303, groups: 2, significant_vars: 8 }
     }

Agent 回報:
"分析完成！共 303 筆資料，8 個變項有顯著差異。"
```

---

## ⛔ Agent 不應該做的事

| 錯誤做法 | 正確做法 |
|----------|----------|
| 用 `cat` 讀取 CSV 內容 | 只傳入檔案路徑 |
| 自己計算統計數值 | 建立統計工單讓系統算 |
| 解析 CSV 判斷欄位類型 | 系統自動判斷 |
| 手動編碼特徵工程 | 系統自動處理 |
| 呼叫多個工具串接 | 一個工單搞定 |

---

## 📊 工單類型

### ML 工單類型
- `automl` - 自動模型選擇（預設）
- `specific` - 指定算法訓練
- `compare` - 算法比較

### 統計工單類型
- `auto_analyze` - 智能自動分析
- `tableone` - 臨床特徵表格
- `eda` - 探索性資料分析
- `survival` - 生存分析 (未來)
- `propensity` - 傾向分數 (未來)

---

## 🔧 系統內部處理（Agent 不需知道）

當 Agent 提交工單後，系統內部會：

1. **驗證**
   - 檔案存在性
   - 欄位有效性
   - 參數合法性

2. **預處理**
   - 缺失值處理
   - 類別編碼
   - 特徵工程

3. **執行**
   - 模型訓練/統計計算
   - 交叉驗證
   - 超參數調整

4. **後處理**
   - 結果格式化
   - 圖表生成
   - 報告產出

5. **儲存**
   - 模型存入 MinIO
   - 結果存入 Redis/MinIO
   - 更新工單狀態

---

## 📝 給 Agent 的提示範本

```
你是一個 AI 助手，可以透過 AutoML MCP 工具進行機器學習和統計分析。

## 可用工具
- list_available_files: 列出可用的資料檔案
- submit_ml_job: 建立機器學習訓練工單
- submit_stats_job: 建立統計分析工單
- get_job_status: 查詢工單狀態
- get_job_result: 取得工單結果

## 工作流程
1. 先用 list_available_files 確認檔案存在
2. 用 submit_*_job 建立工單，取得 job_id
3. 用 get_job_status 輪詢直到完成
4. 用 get_job_result 取得結果

## 重要
- 只傳入檔案路徑，不要讀取檔案內容
- 系統會自動處理資料清理、編碼、訓練
- 等待工單完成後再報告結果
```

---

## 🚀 實作計劃

### Phase 1: 精簡現有工具
- [ ] 移除/隱藏不可用的工具
- [ ] 合併相似功能的工具
- [ ] 統一工單提交介面

### Phase 2: 實作標準工作流程
- [ ] `submit_ml_job` - 統一的 ML 工單入口
- [ ] `submit_stats_job` - 統一的統計工單入口
- [ ] `get_job_result` - 統一的結果取得介面

### Phase 3: 更新 Agent 提示
- [ ] 更新 MCP instruction
- [ ] 加入工作流程範例
- [ ] 測試 Agent 行為
