# MemoriPilot: System Architect

## Overview
This file contains the architectural decisions and design patterns for the MemoriPilot project.

## Architectural Decisions

### 2025-12-16 新增專案管理工具

新增 4 個 MCP 工具於 `statistics_tools.py`：
1. `create_project_workspace` - 建立專案目錄結構（支援 3 種模板）
2. `list_project_workspaces` - 列出 /data/projects/ 下的專案
3. `list_user_visualizations` - 查詢 MinIO 中的圖片
4. `generate_analysis_report` - 從分析結果產生報告

**專案模板：**
- `default`: data/{raw,processed}, analysis, reports, figures
- `medical_study`: 加入 survival, models, roc, km_curves, forest_plots
- `ml_project`: 加入 features, models/{trained,evaluation}, notebooks

**儲存位置：**
- 專案目錄: `/data/projects/{project_name}/`
- 視覺化圖片: MinIO `stats-reports/{user_id}/`
- 分析結果: Redis `stats:result:{result_id}` + MinIO

- Smart Workflow with Ticket System implemented for storage decisions
- Stats service DDD architecture completed
- Accept dependency pattern for dataset registration



- Separated container architecture for AutoML and Statistics services
- Shared Redis for dataset metadata (datasets:{id} key format)
- stats-service reads but doesn't write dataset metadata (dependency on automl-service)
- Direct analyze pattern for CSV content without MinIO storage
- MCP server acts as unified gateway with 32 tools



- 使用 FLAML 作為 AutoML 後端
- FastAPI + Pydantic v2 作為 API 框架
- MinIO 作為檔案存儲（取代本地 CSV 字串傳輸）
- 非同步任務 + WebSocket 推送結果
- User ID + Session ID 資源隔離
- 無認證（僅內網部署）
- Agent 負責上傳檔案到 MinIO，MCP 只檢查檔案



- 使用 FLAML 作為 AutoML 後端（比 auto-sklearn 輕量，適合單節點部署）
- FastAPI + Pydantic v2 作為 API 框架
- 本地檔案存儲（CSV + joblib），後續可換 DB/Object Storage
- MCP Server 透過 HTTP 呼叫 AutoML Server（解耦設計）
- UUID 作為 dataset_id 和 model_id



1. **Decision 1**: Description of the decision and its rationale.
2. **Decision 2**: Description of the decision and its rationale.
3. **Decision 3**: Description of the decision and its rationale.



## Design Considerations

- Data cleaning workflow design needed - how to handle missing values, PII, invalid columns
- Agent vs MCP responsibility boundary for data quality decisions
- User interaction frequency during data cleaning process
- Automated vs manual data cleaning options



- stats-service cannot work independently without automl-service dataset registration
- automl-service should also support direct analyze for pre-training analysis
- stats-service lacks DDD architecture (technical debt)
- Consider shared dataset registration service in future



- 多用戶並發：需要任務佇列管理同時進行的訓練
- WebSocket 連接管理：需處理斷線重連
- MinIO 整合：需要 minio Python client
- Session 管理：考慮 session 過期和清理機制
- 任務佇列：考慮使用 asyncio.Queue 或 Celery



- 多用戶並發：需要考慮資源隔離和任務排隊
- 長時間訓練：建議改為非同步任務機制（job_id + polling）
- 大檔案上傳：CSV 字串傳輸有限制，需考慮 chunk 或檔案上傳
- 認證機制：多用戶場景需要 API key 或 token 認證
- 資源管理：需要 list/delete endpoints 管理資料集和模型



## Components

### automl-service

AutoML REST API with DDD architecture

**Responsibilities:**

- Dataset registration and management
- Training job submission and tracking
- Model management and predictions
- Write dataset metadata to Redis (datasets:{id})

### stats-service

Statistics REST API (routes + infrastructure only, no DDD)

**Responsibilities:**

- EDA report generation
- TableOne summary statistics
- Auto Analyze intelligent analysis
- Direct CSV analysis (no MinIO)
- Read dataset metadata from Redis

### automl-worker

AutoGluon training job consumer

**Responsibilities:**

- Consume jobs from Redis queue
- Execute AutoGluon training
- Save models to MinIO
- Update job status in Redis

### stats-worker

Statistics job consumer

**Responsibilities:**

- Consume jobs from Redis queue
- Execute ydata-profiling EDA
- Execute TableOne generation
- Execute Auto Analyze engine
- Save reports to MinIO

### automl-mcp-server

MCP protocol server with 32 tools

**Responsibilities:**

- Expose 20 AutoML tools
- Expose 12 Statistics tools
- Route requests to appropriate backend service
- Smart orchestration (quick_train, train_and_wait)





### AutoML Server

FastAPI 應用，處理資料集管理、AutoML 訓練、模型推論

**Responsibilities:**

- 驗證 MinIO 檔案存在性和格式
- 非同步執行 AutoML 訓練流程
- 透過 WebSocket 推送進度和結果
- 執行模型預測
- User/Session 資源隔離

### Dataset Store

資料集存儲模組（改用 MinIO）

**Responsibilities:**

- 檢查 MinIO 檔案存在性
- 驗證 CSV 格式正確性
- 註冊資料集元數據（user_id, session_id）
- 按 user/session 過濾資料集

### AutoML Engine

AutoML 訓練引擎（FLAML）

**Responsibilities:**

- 配置 AutoML 參數
- 執行模型搜索和交叉驗證
- 回報訓練進度
- 返回最佳模型和評估指標

### Model Registry

模型持久化模組

**Responsibilities:**

- 使用 joblib 序列化模型
- 存儲模型元數據（含 user_id, session_id）
- 按 user/session 過濾模型
- 支援模型列表和刪除

### Job Manager

非同步任務管理

**Responsibilities:**

- 建立和追蹤訓練任務
- 管理 job 狀態（pending/running/completed/failed）
- 透過 WebSocket 推送狀態更新
- 支援任務取消

### MCP Server

MCP 協議伺服器，暴露 tools 給 Agents

**Responsibilities:**

- 定義 MCP tool schemas
- 傳遞 user_id/session_id 到 AutoML Server
- 處理 WebSocket 連接接收結果
- 格式化響應返回給 Agent

### MinIO

物件存儲服務（外部）

**Responsibilities:**

- 存儲 CSV 資料集檔案
- 提供檔案 URL 給 MCP/AutoML Server
- Agent 負責上傳檔案





### AutoML Server

FastAPI 應用，處理資料集管理、AutoML 訓練、模型推論

**Responsibilities:**

- 接收並存儲 CSV 資料集
- 執行 AutoML 訓練流程
- 載入模型執行預測
- 返回結構化結果

### Dataset Store

資料集存儲模組

**Responsibilities:**

- 生成 UUID 作為 dataset_id
- 將 CSV 存儲到本地檔案系統
- 按 ID 載入資料集為 DataFrame

### AutoML Engine

AutoML 訓練引擎（FLAML）

**Responsibilities:**

- 配置 AutoML 參數
- 執行模型搜索和交叉驗證
- 返回最佳模型和評估指標

### Model Registry

模型持久化模組

**Responsibilities:**

- 使用 joblib 序列化模型
- 存儲模型元數據為 JSON
- 按 ID 載入已訓練模型

### MCP Server

MCP 協議伺服器，暴露 tools 給 Agents

**Responsibilities:**

- 定義 MCP tool schemas
- 驗證 Agent 請求參數
- 轉發請求到 AutoML Server
- 格式化響應返回給 Agent
