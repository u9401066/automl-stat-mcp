# Active Context

## Current Goals

- ## 目前工作重點：實作 AutoML + Stats 系統
- ### ✅ 已確認的技術選型
- | 項目 | 選擇 | 理由 |
- |------|------|------|
- | **AutoML 後端** | AutoGluon | Python 全棧易 debug、效能最佳 |
- | **統計分析** | tableone + pingouin | 臨床研究標準 |
- | **API 框架** | FastAPI | async 支援、自動文檔 |
- | **檔案存儲** | MinIO | Agent 上傳，MCP 驗證 |
- | **任務處理** | 非同步 + WebSocket | 長時間訓練 |
- | **資源隔離** | User ID + Session | 多用戶 |
- | **認證** | 無（內網） | 簡化部署 |
- | **開發風格** | DDD | 開發者偏好 |
- ### 🔍 待評估
- - Python MCP SDK 原生 + FastMCP 與 DDD 的整合方式
- - MCP tool handlers 應放在 Interface Layer
- ### DDD 架構規劃
- ```
- automl-service/
- ├── domain/           # 領域層
- │   ├── models/       # 聚合根、實體、值對象
- │   ├── events/       # 領域事件
- │   └── services/     # 領域服務
- ├── application/      # 應用層
- │   ├── use_cases/    # 用例
- │   ├── dto/          # 資料傳輸對象
- │   └── services/     # 應用服務
- ├── infrastructure/   # 基礎設施層
- │   ├── repositories/ # Repository 實作
- │   ├── ml_engine/    # AutoGluon 整合
- │   └── storage/      # MinIO 整合
- └── interface/        # 介面層
- ├── api/          # FastAPI endpoints
- └── mcp/          # MCP tools
- ```
- ### 下一步
- 用 DDD 架構重新組織 AutoML Service

## Current Blockers

- None yet