# Design Issue #003: 統計分析結果持久化

## 問題描述

目前統計分析工具 (如 `compare_groups`, `analyze_correlations`, `generate_tableone_directly`) 只回傳 JSON 結果，**不會自動儲存到 Redis/MinIO**。

這導致：
1. Agent 需要額外步驟手動儲存結果
2. 分析結果無法追蹤和重現
3. 無法建立分析報告的連結

## 現況分析

### 有儲存功能的工具 ✅

| 工具 | 儲存機制 | 回傳 |
|------|----------|------|
| `handle_missing_values` | 回傳 `csv_content` 供上傳 | csv_content |
| `remove_columns` | 回傳 `csv_content` 供上傳 | csv_content |
| `encode_categorical` | 回傳 `csv_content` 供上傳 | csv_content |
| `submit_automl_job` | 自動存 Redis + MinIO | job_id |
| `submit_tableone_job` | 自動存 Redis | job_id |

### 缺少儲存功能的工具 ❌

| 工具 | 目前回傳 | 應該增加 |
|------|----------|----------|
| `compare_groups` | JSON dict | `result_id` + MinIO 連結 |
| `analyze_correlations` | JSON dict | `result_id` + MinIO 連結 |
| `generate_tableone_directly` | JSON dict | `result_id` + MinIO 連結 |
| `get_quick_stats` | JSON dict | `result_id` (可選) |
| `analyze_missing_values` | JSON dict | `result_id` (可選) |
| `check_multicollinearity` | JSON dict | `result_id` (可選) |
| `compute_roc_curve` | JSON dict | `result_id` + MinIO 連結 |
| `full_classifier_evaluation` | JSON dict | `result_id` + MinIO 連結 |
| `kaplan_meier_survival` | JSON dict | `result_id` + MinIO 連結 |
| `run_propensity_analysis` | JSON dict | `result_id` + MinIO 連結 |

## 建議解決方案

### 方案 A: 統一的結果儲存服務 (推薦)

```python
# 新增 ResultStorage 類別
class ResultStorage:
    def __init__(self, redis_client, minio_client):
        self.redis = redis_client
        self.minio = minio_client

    async def save_result(
        self,
        result: dict,
        user_id: str,
        analysis_type: str,  # "tableone", "correlation", "roc", etc.
        format: str = "json",  # "json", "csv", "markdown"
        ttl: int = 86400 * 7,  # 7 days default
    ) -> dict:
        """
        Save analysis result to Redis (quick access) and MinIO (persistent).

        Returns:
            {
                "result_id": "stat_xxx",
                "redis_key": "stats:result:xxx",
                "minio_path": "results/user_id/analysis_type/xxx.json",
                "expires_at": "2024-12-19T00:00:00Z"
            }
        """
        pass
```

### 方案 B: 每個工具增加 save_result 參數

```python
@mcp.tool()
async def compare_groups(
    csv_path: str,
    numeric_column: str,
    group_column: str,
    save_result: bool = True,  # 新增
    user_id: str = "default",   # 新增
) -> dict:
    """..."""
    result = {...}

    if save_result:
        result_id = await result_storage.save_result(
            result=result,
            user_id=user_id,
            analysis_type="compare_groups",
        )
        result["result_id"] = result_id
        result["result_path"] = f"results/{user_id}/compare_groups/{result_id}.json"

    return result
```

### 方案 C: 使用 Job 系統 (現有機制)

所有分析都透過 Job 系統執行，結果自動存入 Redis：

```python
# 現有的 submit_tableone_job 就是這個模式
job_id = await stats_client.submit_tableone_job(...)
# 結果會存在 Redis: stats:result:{job_id}
```

## 建議實作優先順序

### Phase 1: 高優先級 (常用工具)
1. `generate_tableone_directly` → 加入 MinIO 儲存 Markdown/JSON
2. `compare_groups` → 加入結果儲存
3. `analyze_correlations` → 加入結果儲存 + 熱力圖

### Phase 2: 中優先級 (ROC/模型評估)
4. `compute_roc_curve` → 儲存 ROC 曲線資料 + 圖片
5. `full_classifier_evaluation` → 儲存完整評估報告

### Phase 3: 低優先級 (進階分析)
6. `kaplan_meier_survival` → 儲存生存曲線
7. `run_propensity_analysis` → 儲存完整分析報告

## 檔案結構建議

```
MinIO: automl-results/
├── {user_id}/
│   ├── tableone/
│   │   ├── {timestamp}_{dataset}_tableone.json
│   │   └── {timestamp}_{dataset}_tableone.md
│   ├── correlation/
│   │   ├── {timestamp}_{dataset}_correlation.json
│   │   └── {timestamp}_{dataset}_heatmap.png
│   ├── roc/
│   │   ├── {timestamp}_{model}_roc.json
│   │   └── {timestamp}_{model}_roc_curve.png
│   └── reports/
│       └── {timestamp}_full_analysis.md
```

## Redis 結構建議

```
# 結果索引 (TTL: 7 days)
stats:result:{result_id} = {
    "type": "tableone",
    "user_id": "eric",
    "created_at": "2024-12-12T10:00:00Z",
    "minio_path": "automl-results/eric/tableone/xxx.json",
    "summary": {...}  # 摘要資訊
}

# 使用者結果列表
stats:user:{user_id}:results = [result_id1, result_id2, ...]
```

## 實作檢查清單

- [ ] 建立 ResultStorage 類別
- [ ] 修改 `generate_tableone_directly` 增加儲存
- [ ] 修改 `compare_groups` 增加儲存
- [ ] 修改 `analyze_correlations` 增加儲存
- [ ] 新增 `list_analysis_results(user_id)` 工具
- [ ] 新增 `get_analysis_result(result_id)` 工具
- [ ] 更新文件

## 相關文件

- `docs/design-issues/001-data-cleaning-workflow.md`
- `docs/design-issues/002-csv-path-refactoring.md`
- `automl-mcp-server/src/infrastructure/mcp/handlers/statistics_tools.py`
