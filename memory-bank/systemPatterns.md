# System Patterns

## Architectural Patterns

- Pattern 1: Description

## Design Patterns

- Pattern 1: Description

## Common Idioms

- Idiom 1: Description

## UUID-based Resource Identification

使用 UUID 作為資料集和模型的唯一識別碼，確保多用戶場景下不會有 ID 衝突。dataset_id 和 model_id 都是 UUID 字串。

### Examples

- dataset_store.save_csv_dataset() 返回 UUID
- model_registry.save_model() 返回 UUID
- 所有 API endpoint 使用 ID 來引用資源


## MCP Tool Wrapping Pattern

MCP Server 作為 thin wrapper，將 HTTP API 包裝成 MCP tools。每個 tool 對應一個 HTTP endpoint，負責參數驗證和結果格式化。

### Examples

- upload_dataset tool -> POST /datasets/upload
- automl_train tool -> POST /automl/train
- automl_predict tool -> POST /automl/predict


## Pydantic Schema Validation

使用 Pydantic v2 BaseModel 定義所有請求和響應的資料模型，確保類型安全和自動文檔生成。

### Examples

- UploadDatasetRequest/Response
- AutoMLTrainRequest/Result
- AutoMLPredictRequest/Result
- AutoMLConfig 配置物件


## Async Job + WebSocket Pattern

AutoML 訓練採用非同步任務模式：提交訓練返回 job_id，透過 WebSocket 推送進度和結果。避免 HTTP timeout 和 polling 開銷。

### Examples

- POST /automl/train → 返回 {job_id}
- WebSocket /ws/jobs/{job_id} → 推送進度和結果
- Job 狀態: pending → running → completed/failed


## User/Session Resource Isolation

所有資源（資料集、模型、任務）都綁定 user_id 和可選的 session_id。查詢時自動過濾，確保用戶只能存取自己的資源。

### Examples

- dataset_store.list_datasets(user_id, session_id)
- model_registry.list_models(user_id)
- 所有 API 請求需攼帶 user_id header


## MinIO File Reference Pattern

MCP 不直接處理檔案上傳。Agent 負責上傳檔案到 MinIO 並取得 URL，MCP Server 只負責驗證檔案存在性和格式正確性。解耦大檔案傳輸和 AutoML 邏輯。

### Examples

- Agent: 上傳 CSV 到 MinIO → 取得 minio://bucket/path/file.csv
- MCP tool: register_dataset(minio_url, user_id) → 檢查檔案存在
- AutoML Server: 從 MinIO 讀取檔案進行訓練


## Domain-Driven Design (DDD)

採用 DDD 架構設計，包含：
- Domain Layer: 領域模型、聚合根、值對象、領域事件
- Application Layer: 應用服務、Use Cases、DTO
- Infrastructure Layer: Repository 實作、外部服務整合
- Interface Layer: API Controllers、MCP Tools

待評估：Python MCP SDK + FastMCP 與 DDD 的整合方式

### Examples

- Domain: Dataset, Model, Job, TrainingConfig 領域模型
- Application: TrainModelUseCase, CompareModelsUseCase
- Infrastructure: MinIORepository, AutoGluonMLEngine
- Interface: FastAPI endpoints, MCP tool handlers


## MCP Async Job Pattern

對於長時間運行的任務（如 AutoML 訓練），MCP tool 應該：
1. 立即返回 job_id，不阻塞 MCP 連線
2. 提供 get_job_status tool 讓 Agent 檢查進度
3. 任務完成後，Agent 可透過 get_job_result 取得結果
4. 這樣 Agent 可以在等待時與用戶對話，或執行其他任務

### Examples

- submit_automl_job() → 返回 {job_id, status: 'pending'}
- get_job_status(job_id) → 返回 {status: 'running', progress: 0.5}
- get_job_result(job_id) → 返回 {status: 'completed', model_id, leaderboard}


## Separated Container Architecture

API Container (lightweight, no ML libs) + AutoGluon Worker Container (official image). API submits jobs to Redis queue, Worker consumes and executes. Benefits: 1) Fast API startup, 2) Zero AutoGluon maintenance (just change image tag), 3) Worker horizontal scaling, 4) No local storage (all files in MinIO)

### Examples

- automl-service/Dockerfile - lightweight Python image
- automl-worker/Dockerfile - FROM autogluon/autogluon:x.x.x
- docker-compose.yml - service separation


## Redis Job Queue Pattern

Redis-based job queue for distributing training jobs. API pushes job to Redis list, workers BRPOP to consume. Job status stored in Redis hashes, status updates via Redis pub/sub for real-time WebSocket notifications.

### Examples

- automl-service/src/infrastructure/queue/redis_queue.py
- automl-worker/src/worker.py


## S3 Path Parsing Pattern

\u7d71\u4e00\u89e3\u6790 s3:// \u548c minio:// \u524d\u7db4\u7684\u8def\u5f91\u683c\u5f0f\uff0c\u5728 _parse_path() \u65b9\u6cd5\u4e2d\u5148\u8655\u7406\u524d\u7db4\u518d\u62c6\u89e3 bucket/object \u7d50\u69cb

### Examples

- automl-service/src/infrastructure/file_storage.py: _parse_path() 方法
- automl-worker/src/worker.py: _download_dataset() 方法


## MCP Tool Layering Pattern

MCP Server \u63d0\u4f9b\u4e09\u5c64\u5de5\u5177: 1) Basic Tools - \u76f4\u63a5\u5c0d\u61c9 API \u7684 proxy\uff0c2) Orchestration Tools - \u7d44\u5408\u591a\u500b\u64cd\u4f5c\u7684\u4fbf\u5229\u5de5\u5177\uff0c3) Analysis Tools - \u63d0\u4f9b\u667a\u80fd\u5efa\u8b70

### Examples

- quick_train: register + submit + wait
- train_and_wait: submit + poll + return
- analyze_dataset: 分析資料集提供訓練建議


## Shared Redis Dataset Store

Both automl-service and stats-service share dataset metadata via Redis keys. Format: 'datasets:{dataset_id}' containing JSON with id, name, user_id, minio_path, columns, row_count, created_at. automl-service writes on register_dataset, stats-service reads for analysis jobs. This enables loose coupling but creates implicit dependency.

### Examples

- automl-service/src/infrastructure/redis_dataset_store.py
- stats-service/src/infrastructure/redis_dataset_store.py
- automl-service/src/infrastructure/repositories.py (RedisDatasetRepository.save calls redis_dataset_store.save)


## Direct Analyze Pattern

Support for analyzing CSV data without MinIO storage. CSV content is passed directly in the request body (optionally base64 encoded for large files). Results are returned directly or stored temporarily in Redis. Useful for one-time analysis, testing, and small datasets.

### Examples

- stats-service/src/routes/direct.py
- analyze_csv_directly MCP tool
- get_quick_stats MCP tool


## Documentation Preservation Policy

因為專案太複雜（多微服務、82 MCP tools、DDD 架構），所有程式碼中給維護人員看的註解和文檔必須保留：
1. 檔案頂部的 docstring（說明用途、用法、執行方式）
2. 分區註解（如 # ===== Section Name ===== ）
3. 類別和函數的 docstring
4. 參數說明和回傳值說明
5. 使用範例和 Run 指令
這些文檔可以更新內容，但不能刪除。確保新進維護人員能快速理解程式碼。

### Examples

- stats-worker/tests/test_public_datasets.py - 頂部完整說明測試目的、資料集、執行方式
- 每個 test class 有 docstring 說明測試對象
- 分區用 # ======= 區分不同功能區塊


## Docker Container Conflict Resolution

Docker Compose 啟動時處理 container 名稱衝突的策略：

1. **檢查現有 container 狀態**:
   - `running`: 直接複用，跳過該服務
   - `exited/created`: 移除後重建
   - 不存在: 正常建立

2. **共用基礎服務**: Redis 等常被多專案共用，若已運行且健康就直接連接

3. **啟動腳本**: `scripts/docker-start.sh`
   - `./scripts/docker-start.sh` - 智慧啟動（複用健康服務）
   - `./scripts/docker-start.sh --clean` - 清理後重啟
   - `./scripts/docker-start.sh --status` - 只檢查狀態

4. **健康檢查端點**:
   - stats-service: http://localhost:8003/health
   - automl-api: http://localhost:8001/health
   - automl-mcp: http://localhost:8002/health
   - Redis: `docker exec automl-redis redis-cli ping`

### Examples

- scripts/docker-start.sh - 智慧啟動腳本
- docker ps -a --filter 'name=automl' 檢查狀態
- docker rm container_name 移除停止的 container


## MCP File Upload Workflow

檔案上傳採用「路徑傳遞」模式，避免 Copilot 經手檔案內容：

流程：
1. Agent 呼叫 list_available_files() 查看可用檔案
2. Agent 詢問使用者選擇上傳方式：
   - local: 從掛載目錄上傳 (/data/sample_data, /data/uploads)
   - minio: 引用現有 MinIO 檔案
3. Agent 呼叫 upload_dataset(source_type, source_path)
4. MCP Server 讀取檔案、上傳到 MinIO、驗證成功
5. 回傳 dataset_id 和後續步驟提示

Volume Mounts (docker-compose.yml):
- ./sample_data:/data/sample_data:ro
- ./uploads:/data/uploads:ro
- ./datasets:/data/datasets:ro
- ./processed:/data/processed (可寫，存放清理後檔案)

### Examples

- upload_tools.py - list_available_files(), upload_dataset(), get_upload_help()
- docker-compose.yml - automl-mcp volumes section
- automl-service datasets.py - /datasets/upload endpoint


## Data Cleaning Integration Pattern

資料清理整合到 Stats Service，而非獨立服務：

設計決策理由：
1. 資料清理是統計分析的前置步驟，邏輯上相關
2. 避免服務過度拆分
3. Stats Service 已有 pandas 環境
4. 可共用 Redis + MinIO 基礎設施

架構：
```
MCP Server (cleaning_tools.py)
    │
    ├─→ 同步清理 → Stats Service /cleaning/* API
    │               ├─ /cleaning/convert-binary
    │               ├─ /cleaning/encode-categorical
    │               ├─ /cleaning/handle-missing
    │               └─ /cleaning/column-info
    │
    └─→ 處理過的檔案存到 /data/processed/{user_id}/
```

MCP Tools:
- convert_to_binary: 轉換欄位為 0/1（傾向分數分析必需）
- encode_categorical: 類別編碼 (Label/OneHot)
- handle_missing_values: 缺失值處理
- remove_columns: 移除欄位
- filter_rows: 篩選資料列
- get_column_info: 取得欄位資訊

### Examples

- automl-mcp-server/handlers/cleaning_tools.py - MCP 工具定義
- stats-service/routes/cleaning.py - Stats Service API（待實作）
- /data/processed/{user_id}/*.csv - 處理後檔案存放位置


## Column Name Sanitization Pattern

上傳時自動清理 Excel 來源的欄位名稱：

規則：
1. 特殊符號替換為底線：空格、括號、斜線、加號、減號等
2. 保留中文字元（常見於研究資料）
3. 移除 Excel 殘留的 `Unnamed:` 前綴
4. 連續底線合併為單一底線
5. 移除首尾底線

Metadata JSON 輸出：
```json
{
  "original_file": "...",
  "processed_file": "...",
  "timestamp": "...",
  "column_mapping": {
    "changed": {"Ropica(ML)": "Ropica_ML", ...},
    "unchanged": ["年齡", "性別", ...]
  },
  "total_columns": 142,
  "columns_renamed": 84
}
```

### Examples

- upload_tools.py - _sanitize_column_name(), _create_column_mapping()
- /data/processed/{user_id}/*_metadata.json - 對照表



## JSON Sanitization for Statistical Results

統計計算結果可能包含 NaN、Infinity 等 Python/NumPy 特殊值，這些無法直接 JSON 序列化。使用 sanitize_for_json() 遞迴處理所有資料：NaN → null, Infinity → "Infinity", np.floating → float。此函數在 save_report() 儲存到 MinIO 前調用。

### Examples

- stats-worker/src/worker.py: sanitize_for_json()
- stats-worker/src/worker.py: save_report() 使用 sanitize_for_json


## Visualization Module Pattern (Phase 8)

統計分析結果自動產生視覺化圖表。每種分析類型有對應的繪圖函數，統一使用 matplotlib backend。所有圖表函數遵循相同介面：接受資料、可選 ax 參數、返回 Figure 物件。

模組結構：
- visualization/survival.py - 生存分析（KM曲線、風險圖）
- visualization/roc.py - ROC/PR 曲線分析
- visualization/group_comparison.py - 組間比較（箱形圖、直方圖）
- visualization/automl.py - AutoML 結果（特徵重要性、SHAP、學習曲線）

設計原則：
1. 每個函數專注單一圖表類型
2. 支援傳入 ax 參數整合到子圖
3. 錯誤時 graceful degradation（返回空圖而非拋錯）
4. 高階 helper 函數組合多個圖表

### Examples

- visualization/survival.py: plot_kaplan_meier(), plot_cumulative_hazard()
- visualization/roc.py: plot_roc_curve(), plot_roc_with_ci()
- visualization/automl.py: plot_feature_importance(), plot_shap_summary()
- visualization/__init__.py: 統一導出所有繪圖函數


## Local Results Storage Pattern (Phase 8)

除了 MinIO 雲端儲存，同時提供本地目錄結構讓使用者直接瀏覽分析結果。

目錄結構：
```
/data/results/{user_id}/{job_name}_{timestamp}/
├── metadata.json      # 任務元資料
├── report.json        # JSON 格式報告
├── report.html        # HTML 可視化報告
├── figures/           # 圖表 PNG 檔案
│   ├── roc_curve.png
│   ├── feature_importance.png
│   └── ...
└── data/
    └── source_info.json  # 資料來源追蹤
```

實作元件：
- JobResultsManager: 管理目錄建立、檔案儲存
- WorkerResultsMixin: Worker 整合 mixin
- RESULTS_BASE_PATH: 可配置基礎路徑

優點：
1. 使用者可直接瀏覽檔案系統存取結果
2. HTML 報告可用瀏覽器開啟
3. 圖表可直接複製到報告中
4. MinIO 仍作為備份和 API 存取

### Examples

- stats-worker/src/results/manager.py: JobResultsManager 類別
- stats-worker/src/results/worker_mixin.py: WorkerResultsMixin
- docker-compose.yml: ./results:/data/results volume mount


## Worker Mixin Pattern

使用 Mixin 類別為 Worker 添加可選功能，保持主類別簡潔。Mixin 提供特定功能的方法，Worker 透過多重繼承獲得這些功能。

好處：
1. 功能解耦：Local Results 相關邏輯在 WorkerResultsMixin
2. 可選性：可選擇是否繼承 Mixin
3. 測試簡單：Mixin 可獨立測試
4. 擴展容易：新功能寫新 Mixin

使用方式：
```python
class StatsWorker(WorkerResultsMixin):
    def process_job(self, job):
        # 使用 mixin 方法
        manager = self.create_job_results_manager(job)
        # ...處理...
        self.finalize_job_with_local_results(manager, result)
```

### Examples

- stats-worker/src/results/worker_mixin.py: WorkerResultsMixin
- stats-worker/src/worker.py: class StatsWorker(WorkerResultsMixin)


## Research-Driven Analysis Workflow

系統化研究分析流程：

1. **計畫先行** - 先建立 RESEARCH_PLAN.md 定義分析步驟
2. **變更追蹤** - 使用 CHANGELOG.md 記錄每次分析
3. **標準化目錄結構**:
   ```
   project/
   ├── data/{raw,cleaned,analysis}/
   ├── results/{01_descriptive,02_univariate,03_multivariate,04_model}/
   └── reports/figures/
   ```
4. **命名規則**:
   - 資料: `{專案}_{用途}_{日期}.csv`
   - 圖表: `fig_{類型}_{變數}_{結果}.png`
   - 表格: `tbl_{類型}_{內容}.csv`
5. **分階段執行** - Phase 1-5 依序完成
6. **MCP 工具對應** - 每個步驟指定使用的 MCP 工具

### Examples

- projects/painless_胃鏡/RESEARCH_PLAN.md
- projects/painless_胃鏡/CHANGELOG.md
