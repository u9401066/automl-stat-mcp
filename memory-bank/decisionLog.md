# Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-16 | 整合 template-is-all-you-need 框架 | 引入憲法-子法層級規則系統、Claude Skills 自動化、Memory Bank 規範。統一專案規範，提升 AI 輔助開發效率。 |
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
| 2025-12-03 | Stats Service Dataset Dependency - Accept dependency pattern | 1. Direct analysis endpoints already provide independent analysis capability (/direct/analyze, /direct/quick-stats). 2. Requiring dataset registration for tracked analysis is a valid design - single source of truth for dataset metadata. 3. Avoids overengineering (no separate registration service or duplicated logic). 4. Usage patterns are clear: use direct endpoints for ad-hoc analysis, use dataset_id for ML pipeline integration. |
| 2025-12-03 | Smart Workflow with Ticket System for Data Analysis | Implemented 3 new MCP tools: start_data_analysis (creates ticket with preview), execute_analysis_ticket (user chooses temp vs persistent), check_analysis_progress (track jobs). This provides guided UX for AI agents, letting users decide on storage before analysis begins. |
| 2025-12-03 | PII handling分為兩種類型：PII_DETECTED（整欄是PII可刪除/遮罩）和 PII_EMBEDDED（散佈的PII需要PHI MCP處理） | 整欄明顯是PII的情況（如email, phone欄位）可以用簡單的刪除或遮罩處理。但如果PII散佈在其他文字資料中（如notes欄位偶爾出現email），無法簡單處理，需要專門的PHI MCP來做細緻的去識別化處理。 |
| 2025-12-03 | Phase 1 統計分析增強使用獨立的 advanced_analysis.py 模組 | 將高級分析功能（相關性、分布比較、缺失值、VIF）整合到單一模組中，使用 dataclass 返回結構化結果，便於序列化為 JSON 供 MCP 工具使用。使用 bridge module (stats_worker_tasks.py) 連接 MCP server 和 stats-worker。 |
| 2025-12-04 | 統計分析套件架構：保持 ydata-profiling + tableone + scipy + statsmodels + lifelines 的組合，各司其職 | 每個套件有不可替代的功能：ydata-profiling (EDA報告)、tableone (臨床Table 1)、scipy (基礎檢定)、statsmodels (Power Analysis + 進階迴歸，無替代方案)、lifelines (存活分析)。臨床研究 AutoML 系統必須具備這些能力。 |
| 2025-12-04 | Phase 6.3 Survival Power Analysis implemented using Schoenfeld formula with anti-recursion pattern | 1. Schoenfeld (1981) formula is the standard for log-rank test power calculation. 2. Added _include_sensitivity parameter to prevent infinite recursion between calculate_events/sample_size and their sensitivity methods. 3. Supports hazard ratio, median survival, event-based calculations for comprehensive clinical trial planning. 4. 45 tests covering formula verification, clinical scenarios, and edge cases. |
| 2025-12-04 | Identified 11 Python files exceeding 500 lines requiring DDD refactoring | statistics_tools.py (3407 lines) and power_analysis.py (2827 lines) are the highest priority for refactoring. Both violate Single Responsibility Principle with multiple unrelated functionalities. Plan: split into domain-specific modules following DDD patterns. Target: max 800 lines per file. |
| 2025-12-04 | 所有程式碼檔案中給維護人員看的註解和文檔（docstring, 用法說明, 結構分區等）必須保留，只能更新不能刪除 | 因為這個專案太複雜了，包含多個微服務（automl-service, stats-service, automl-worker, stats-worker, mcp-server）、82 個 MCP tools、DDD 架構、多種統計分析功能，維護人員需要這些文檔來理解程式碼結構和用法 |
| 2025-12-08 | Docker Compose 啟動時若遇到 container 名稱衝突，應先檢查現有 container 狀態：若已運行且健康則直接複用，若停止則移除後重建，而非直接報錯退出 | 開發環境中常有多個專案共用 Redis 等基礎服務，或上次異常關閉留下的 container。智慧處理衝突可提升開發體驗，避免手動清理的繁瑣步驟。 |
| 2025-12-08 | MCP File Upload Architecture: Local Volume Mount + Interactive Workflow | 問題：原本設計讓 Copilot 讀取檔案內容再傳給 MCP，這會：
1. 浪費大量 token（CSV 可能很大）
2. 大檔案會被截斷，資料不完整
3. 增加不必要的複雜度

解決方案：
1. Volume Mount：MCP Server 掛載本地資料夾 (sample_data, uploads, datasets)
2. Interactive Workflow：
   - Agent 呼叫 upload_dataset
   - MCP 提示使用者選擇方式（local file 或 MinIO path）
   - 使用者選完後 Agent 傳給 MCP
   - MCP 直接讀取檔案並上傳
   - 回傳 dataset_id 和後續步驟提示

新增 Tools：
- list_available_files(): 列出可用檔案
- upload_dataset(): 上傳資料集（支援 local 和 minio 兩種模式）
- get_upload_help(): 取得上傳說明

關鍵改變：Copilot 只傳「檔案路徑」，不經手檔案內容 |
| 2025-12-08 | Dataset Upload 支援兩種儲存模式: Temporary (Redis) vs Permanent (MinIO) | 需求：不是所有上傳都需要永久保存
- Temporary (Redis): 一次性分析，存在 Redis 隨 job 過期，適合快速探索
- Permanent (MinIO): 永久存檔，可重複使用，適合 ML 訓練

上傳前必須詢問使用者：
1. 資料來源：local file 或 MinIO path
2. 儲存方式：暫存 (temporary) 或 永久存檔 (permanent)

工具回傳：
- temporary → job_id (用於 get_stats_job_result)
- permanent → dataset_id (用於 submit_automl_job 或 auto_analyze) |
| 2025-12-09 | Upload 時自動清理 Excel 來源的欄位名稱，保留原始對照表供參考 | 問題：真實研究資料來自 Excel，欄位名稱常有：
1. 特殊符號（括號、斜線、加號）
2. 空格
3. 中英文混合
4. Excel 產生的 "Unnamed:" 前綴

解決：upload_dataset 時自動清理欄位名稱
- 規則：特殊符號→底線，保留中文，移除 Unnamed:
- 輸出：處理過的 CSV + Metadata JSON（原始↔清理後對照）
- 位置：/data/processed/{user_id}/*.csv + *_metadata.json |
| 2025-12-09 | Data Cleaning 整合到 Stats Service 而非獨立服務 | 三個選項：
A) 嵌入現有 MCP Server（已嘗試）- MCP Server 會變胖
B) 獨立 Cleaning Service - 服務過多
C) 整合到 Stats Service（選擇）- 邏輯相關，共用環境

決定採用 C 的理由：
1. 資料清理是統計分析的前置步驟，邏輯上相關
2. 避免服務過度拆分（已有 5 個服務）
3. Stats Service 已有 pandas 環境
4. 可共用 Redis + MinIO 基礎設施

實作計畫：
- Stats Service 新增 /cleaning/* API endpoints
- MCP cleaning_tools.py 呼叫 Stats Service API
- 清理後檔案存到 /data/processed/{user_id}/ |

| 2025-12-09 | Worker 結果存儲只保留統計摘要，不存儲原始資料陣列 | Propensity score 分析原本會將完整的分數陣列（數千個值）存到 MinIO。這既浪費存儲空間，對使用者也沒有意義。改為只存儲統計摘要（mean, std, min, max, percentiles）。如果需要完整分數用於後續分析，可透過 include_scores=True 參數在內部流程中取得。 |
| 2025-12-09 | Phase 8 Visualization Service 採用 Matplotlib + Seaborn 生成出版品質圖表 | 現狀：系統只返回數據（figure_data），不生成圖片。問題：用戶需要視覺化結果（ROC曲線、KM曲線、森林圖等）。決定：1. 採用 Matplotlib + Seaborn（出版品質、300dpi、無需前端）2. 圖片存 MinIO，返回 URL 陣列 3. 返回格式新增 `visualizations[]` 4. 分 5 個子階段實施（8A基礎-8E整合）5. 先實作 P0 圖表：ROC、PR、KM、森林圖、直條圖+p-value。設計文件：docs/design-issues/003-visualization-service.md |
| 2025-12-10 | 研究分析專案採用 Agent-Driven Workflow，完全不寫 Python code | MCP Tools 已提供完整分析能力 (資料清理、描述統計、ROC 分析、AutoML)。Agent 只需讀取 AGENT_WORKFLOW.yaml 並依序呼叫工具。這樣更符合 AI Agent 的設計理念，也讓工作流程可重複、可追蹤。 |
| 2025-12-10 | MinIO 架構：只使用遠端實例 (192.168.1.102:9000)，禁止本地重複部署 | 問題：發現本地有空的 MinIO 容器 (localhost:9000)，導致 Agent 下載分析圖表失敗 (403 錯誤)。根因：stats-worker 上傳到遠端 MinIO，但 Agent 誤從本地空的 MinIO 下載。

修復措施：
1. 停止並移除本地 MinIO 容器
2. 確認環境變數 MINIO_ENDPOINT=192.168.1.102:9000
3. 所有服務使用同一個遠端 MinIO 實例

設計原則：
- 共用基礎設施只部署一份（避免資源浪費和狀態不一致）
- 本地開發環境連接遠端 MinIO（已在 .env 配置）
- Agent 下載 MinIO 檔案需使用 Python minio client（不是 curl/wget） |
| 2025-12-11 | 儲存架構改為 Redis (暫存+TTL) + MinIO (永久儲存), 完全移除本地檔案儲存 | 1. 避免重複儲存造成空間浪費和同步問題 2. Redis TTL 自動清理過期資料 3. MinIO 提供可靠的永久儲存 4. 簡化架構，減少維護負擔 |
