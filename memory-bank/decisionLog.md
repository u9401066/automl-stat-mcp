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
