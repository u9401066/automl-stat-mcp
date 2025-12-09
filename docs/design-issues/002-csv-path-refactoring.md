# CSV Path Refactoring - 2025-12-09

## 問題
所有 statistics tools 原本使用 `csv_content` 參數，Agent 需要直接傳遞 CSV 資料內容。

**問題：**
1. 浪費 token（大檔案可能數萬行）
2. 可能被截斷
3. 不符合 E2E 設計原則（Agent 應只傳路徑）

## 解決方案

### 1. 新增 Helper Function
```python
def _read_csv_from_path_or_reject(csv_path_or_content: str) -> Tuple[bool, Union[str, Dict]]:
    """
    智能檢測輸入是路徑還是資料內容：
    - 如果是路徑 → 讀取檔案，返回內容
    - 如果是資料 → 拒絕，返回錯誤訊息指導用戶使用 upload_dataset
    """
```

### 2. 修改所有 Direct Tools
將 `csv_content: str` 改為 `csv_path: str`

**已修改的工具（共 20+）：**
- analyze_csv_directly
- analyze_correlations
- analyze_missing_values
- check_multicollinearity
- compare_groups
- compare_roc_curves
- compare_multiple_roc_curves
- run_full_statistical_analysis
- generate_tableone_directly
- get_tableone_preview
- kaplan_meier_survival
- cox_proportional_hazards
- compare_survival
- survival_data_summary
- estimate_propensity_scores
- match_propensity_scores
- estimate_treatment_effect
- compute_roc_curve
- find_optimal_threshold
- interactive_threshold_analysis
- generate_roc_publication_report

### 3. 錯誤處理
如果 Agent 誤傳資料內容，會返回友善的錯誤訊息：
```json
{
  "status": "error",
  "error_type": "DATA_CONTENT_NOT_ALLOWED",
  "message": "Please use file PATH instead of CSV content",
  "guidance": {
    "1": "Use list_available_files() to see available files",
    "2": "Pass the file PATH: csv_path='/data/sample_data/your_file.csv'"
  }
}
```

## 正確的 E2E 流程

### 方式 A：使用 Direct Tools（推薦用於分析）
```
Agent: csv_path="/data/sample_data/iris.csv"
  ↓
MCP Server: 讀取檔案 → 執行分析 → 返回結果
```

### 方式 B：使用 Upload + Dataset-based Tools（推薦用於 ML 訓練）
```
Agent: upload_dataset(source_path="/data/sample_data/iris.csv", storage_mode="permanent")
  ↓
MCP Server: dataset_id
  ↓
Agent: submit_automl_job(dataset_id=..., target_column="species")
```

## 掛載路徑
```yaml
volumes:
  - ./sample_data:/data/sample_data
  - ./uploads:/data/uploads
  - ./datasets:/data/datasets
```

## 驗證
```bash
# 確認容器內程式碼已更新
docker exec automl-mcp grep "csv_path" /app/src/infrastructure/mcp/handlers/statistics_tools.py | head -5
```
