# Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-02 | 採用 FLAML 作為 AutoML 後端 | FLAML 比 auto-sklearn 輕量，安裝簡單，適合單節點 CPU only 部署環境。效能足夠處理 tabular data 的分類和回歸任務。 |
| 2025-12-02 | 三層架構分離：AutoML Server + Core Library + MCP Server | 解耦設計，便於獨立開發、測試和部署。MCP Server 透過 HTTP 呼叫 AutoML Server，後續可輕鬆替換 AutoML 後端或擴展為多節點。 |
| 2025-12-02 | 多用戶透過各自 Agent 存取 MCP Server | 用戶不直接操作系統，而是透過 AI Agent 互動。Agent 呼叫 MCP tools 執行 AutoML 任務，取得結果後與用戶進行後續討論。這種設計讓技術複雜度對用戶透明。 |
| 2025-12-02 | 採用非同步任務 + WebSocket 處理長時間訓練 | AutoML 訓練可能需要數分鐘到數小時，同步 HTTP 會 timeout。使用非同步任務機制：提交訓練返回 job_id，透過 WebSocket 推送進度和結果，避免 polling 開銷。 |
| 2025-12-02 | User ID + Session 隔離資源 | 多用戶場景需要資源隔離。每個用戶只能看到自己的資料集和模型，可能進一步用 session 區分不同工作階段。確保資料安全和避免資源衝突。 |
| 2025-12-02 | 無認證（內網部署）+ MinIO 檔案存儲 | 僅內網使用不需要認證機制。MCP 無法直接傳檔案，改用 MinIO 物件存儲：Agent 上傳檔案到 MinIO 取得連結，MCP Server 只負責檢查檔案存在性和格式正確性。解耦檔案傳輸和 AutoML 邏輯。 |
| 2025-12-02 | 選擇 AutoGluon 作為 AutoML 後端 | 1. 整個 stack 都是 Python，易於 debug（不會 Java）
2. Kaggle 競賽表現最佳，準確度高
3. 支援指定算法、比較算法、自動 ensemble
4. 內建 leaderboard() 功能
5. 有官方 Docker image
6. 雖然需要自己包 REST API，但可以完全掌控 |
| 2025-12-02 | 採用 DDD（Domain-Driven Design）開發風格 | 開發者偏好 DDD 架構。需要評估 Python MCP SDK 原生 + FastMCP 是否適合 DDD 模式。先記錄此偏好，實作時盡量遵循 DDD 原則：領域模型、聚合根、Repository 模式、Application Service 等。 |
| 2025-12-02 | MCP AutoML 採用 Async Job Pattern 避免長時間阻塞 | AutoML 訓練可能需要數分鐘到數小時，MCP tool 呼叫不能阻塞這麼久。採用非同步任務模式：
1. submit_automl_job - 立即返回 job_id（MCP call 馬上結束）
2. get_job_status - Agent 可以輪詢檢查進度
3. 訓練完成後，Agent 可以取得結果並與用戶討論

參考 medical-calc-mcp 的 DDD + FastMCP 架構實作。 |
| 2025-12-02 | 採用 Separated Container Architecture: API Container (lightweight) + AutoGluon Worker Container (official image) | 1. API container 不裝 AutoGluon，只處理 REST API 和 Redis 通訊，啟動快、image 小 2. AutoGluon worker 用官方 image，更新只需換 FROM tag，零維護 3. MinIO 為外部服務，只連線不存本地資料 4. 透過 Redis queue 分發 jobs，支援 worker 水平擴展 |
| 2025-12-02 | AutoGluon 1.3.1 \u4f7f\u7528\u5b98\u65b9 Docker \u93e1\u50cf autogluon/autogluon:1.3.1-cpu-framework-ubuntu22.04-py3.11 | \u907f\u514d\u624b\u52d5\u5b89\u88dd\u4f9d\u8cf4\u554f\u984c\uff0c\u7c21\u5316\u90e8\u7f72\u6d41\u7a0b\uff0c\u6b64\u93e1\u50cf\u5305\u542b\u5b8c\u6574\u7684 CPU \u63a8\u8ad6\u74b0\u5883 |
| 2025-12-02 | \u4f7f\u7528 predictor.model_best \u5c6c\u6027\u800c\u975e get_model_best() \u65b9\u6cd5 | AutoGluon 1.3.x API \u8b8a\u66f4\uff0cget_model_best() \u5df2\u79fb\u9664\uff0c\u6539\u7528\u5c6c\u6027\u5b58\u53d6\u65b9\u5f0f |
| 2025-12-02 | MCP Server \u5347\u7d1a\u70ba\u667a\u80fd Job Orchestrator\uff0c\u800c\u975e\u55ae\u7d14 API Proxy | \u63d0\u4f9b\u66f4\u597d\u7684 Agent UX\uff0c\u6e1b\u5c11 Agent \u8981\u505a\u7684\u5de5\u4f5c\u3002\u65b0\u589e 5 \u500b\u667a\u80fd\u5de5\u5177: quick_train, train_and_wait, wait_for_job, analyze_dataset, get_training_summary |
| 2025-12-02 | Worker \u652f\u63f4 GPU \u81ea\u52d5\u5075\u6e2c\u8207 CPU fallback\uff0c\u4e26\u652f\u63f4\u6c34\u5e73\u64f4\u5c55 | \u4f7f\u7528 PyTorch torch.cuda.is_available() \u5075\u6e2c GPU\uff0c\u900f\u904e ag_args_fit num_gpus \u63a7\u5236\u8a13\u7df4\u88dd\u7f6e\u3002Worker \u5728 Redis \u8a3b\u518a\u81ea\u5df1\u4ee5\u652f\u63f4\u76e3\u63a7\u548c\u64f4\u5c55\u3002 |
| 2025-12-02 | Refactoring: 移除重複程式碼和未使用的檔案 | 1. storage/minio_client.py 與 file_storage.py 重複功能，統一使用 file_storage.py
2. job_worker.py 和 ml_engine.py 已被獨立的 Worker container 取代，API container 不需要 AutoGluon
3. config.py 改為只包含外部服務設定（MinIO/Redis/API），本地目錄設定移到 repositories.py
4. repositories.py 使用 PERSIST_DIR 環境變數，方便 Docker volume mount |
| 2025-12-02 | Docker Compose 預設 4 個 Worker 並整合所有服務 | 1. 一鍵啟動：docker compose up -d 啟動全部服務（Redis、API、MCP、4x Worker）
2. 4 個 Worker 可同時處理 4 個訓練任務，適合多人使用
3. 可透過 --scale automl-worker=N 動態調整 Worker 數量
4. 移除 docker-compose.scale.yml，簡化部署流程 |
| 2025-12-03 | 採用獨立 Stats Service 架構（方案 A 改良版），共用 Redis 和 MinIO | 1. 獨立部署、獨立擴展，不影響現有 AutoML 服務
2. 統計分析（EDA）可能耗時，使用獨立 Worker 避免阻塞
3. 共用 Redis 佇列機制，保持一致的 Job 處理模式
4. MinIO 只存最終結果（JSON/HTML 報告）
5. MCP Server 統一入口，Agent 無需知道後端是哪個服務 |
| 2025-12-03 | 選用 ydata-profiling + tableone 作為統計分析套件 | 1. ydata-profiling: 一行產出完整 EDA 報告，支援 JSON 輸出適合 API
2. tableone: 標準 Table 1 格式，已有學術引用（JAMIA Open），適合醫學/臨床研究
3. 不選 statsmodels: 太低階，需要大量包裝才能自動化
4. 兩者可以互補：ydata-profiling 做探索性分析，tableone 做研究報告 |
| 2025-12-03 | Stats Service \u63a1\u7528\u7368\u7acb\u670d\u52d9\u67b6\u69cb (stats-service + stats-worker)\uff0c\u8207 AutoML \u5171\u4eab Redis/MinIO \u57fa\u790e\u8a2d\u65bd | 1. \u9694\u96e2\u6027\uff1aAutoML \u548c Stats \u7684\u5957\u4ef6\u4f9d\u8cf4\u5b8c\u5168\u4e0d\u540c\uff0c\u7368\u7acb\u670d\u52d9\u907f\u514d\u7248\u672c\u885d\u7a81\u30022. \u64f4\u5c55\u6027\uff1a\u53ef\u7368\u7acb\u64f4\u5c55 worker \u6578\u91cf\uff08AutoML 4\u500b, Stats 2\u500b\uff09\u30023. \u7dad\u8b77\u6027\uff1a\u53ef\u7368\u7acb\u66f4\u65b0\u90e8\u7f72\u30024. \u8cc7\u6e90\u5171\u4eab\uff1a\u5171\u7528 Redis queue \u548c MinIO \u5132\u5b58\uff0c\u6e1b\u5c11\u57fa\u790e\u8a2d\u65bd\u8907\u96dc\u5ea6\u3002 |
| 2025-12-03 | 實作 auto_analyze 智能統計分析工具，備案是讓 Agent 自己決定跑哪些分析 | 1. 主方案：auto_analyze 一個工具自動執行所有統計分析，依資料特性自動選擇適當方法。2. 優點：簡化 Agent 使用，不需要統計知識就能獲得完整分析。3. 備案：如果過於複雜或某些場景需要精細控制，Agent 可以使用獨立的統計工具（如現有的 submit_eda_job, submit_tableone_job 等）自行組合分析流程。 |
| 2025-12-03 | Shared Redis Dataset Store Pattern - Both automl-service and stats-service share dataset metadata via Redis key 'datasets:{id}' | Stats service needs to access dataset metadata (minio_path, columns) for analysis jobs. Instead of HTTP calls between services, both services read/write to the same Redis keys. automl-service writes on register_dataset, stats-service reads for analysis jobs. This reduces coupling but creates a dependency: stats-service can only analyze datasets that were first registered via automl-service. |
| 2025-12-03 | Direct Analyze Pattern - Support CSV analysis without MinIO storage | For quick one-time analysis or testing with small datasets, users shouldn't need to upload to MinIO first. stats-service has /direct/analyze and /direct/quick-stats endpoints that accept CSV content directly in the request body. The analyze_csv_directly MCP tool exposes this. automl-service should also support this pattern for pre-training dataset analysis. |
| 2025-12-03 | Identified Architecture Gap - Stats service depends on automl-service for dataset metadata | Use Case 3 (stats analysis) requires dataset metadata in Redis, but only Use Case 1 (automl training) writes this metadata. This means stats-service cannot work independently. Options: (A) Add dataset registration to stats-service, (B) Create shared registration service, (C) Document as intentional dependency. Decision deferred pending user requirements. |
