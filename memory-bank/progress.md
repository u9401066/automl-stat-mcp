# Progress (Updated: 2025-12-03)

## Done

- AutoML MCP System 核心功能完成
- MCP Server 模組化重構 (20 tools)
- 企業 HTTPS 部署支援 (POST-only API)
- 完整部署文件 (deployment-guide.md)
- MinIO 安裝指南

## Doing

- Stats Service 架構規劃
- ydata-profiling + tableone 整合評估

## Next

- 建立 stats-service (FastAPI, port 8003)
- 建立 stats-worker (ydata-profiling, tableone)
- MCP Server 加入 stats tools
- 更新 docker-compose 整合新服務
