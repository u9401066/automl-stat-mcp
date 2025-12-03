# Active Context

## Current Goals

- 正在擴展 AutoML MCP System，加入自動統計分析功能：
- ## 目前狀態
- - AutoML 核心功能完成（20 MCP tools）
- - 企業 HTTPS 部署支援完成
- - 文件完整（deployment-guide.md）
- ## 進行中
- - 規劃 Stats Service 架構
- - 準備實作 stats-service + stats-worker
- ## 新增組件規劃
- 1. stats-service (port 8003): FastAPI, EDA/TableOne endpoints
- 2. stats-worker: ydata-profiling, tableone
- 3. MCP stats tools: generate_eda_report, generate_tableone, get_stats_job_status
- ## 架構決策
- - 獨立服務，共用 Redis + MinIO
- - 複用現有 Job 機制（submit → poll → result）

## Current Blockers

- None yet