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
