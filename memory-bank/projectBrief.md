# AutoML MCP System

## Purpose

Define the main purpose of this project.

## Target Users

Describe who will use this.


## Project Summary

Multi-user AutoML system enabling AI Agents to train and compare ML models via MCP protocol. Uses async job pattern to avoid blocking during long-running training.



AutoML + MCP Server 系統：讓多用戶透過 AI Agent 請求 MCP Server，執行 AutoML 訓練和預測，返回結果供 Agent 與用戶進行後續討論。主要應用於臨床/研究資料集的機器學習自動化。



## Goals

- Enable AI Agents to perform AutoML via MCP
- Support multi-user with resource isolation
- Non-blocking async training jobs
- Zero maintenance for AutoGluon updates (use official Docker image)
- DDD architecture for maintainability



- 建立 AutoML 微服務（FastAPI），支援資料集上傳、模型訓練、推論
- 建立 MCP Server 包裝 AutoML API 為 MCP tools
- 支援多用戶透過各自的 Agent 同時使用
- Agent 取得結果後可與用戶進行互動式討論
- 主要處理 tabular data（臨床/研究資料集）



## Constraints

- MinIO is external server (connect only, no local storage)
- AutoGluon runs in separate container (not in API)
- MCP calls must return immediately (use job queue pattern)



- 單節點 VM 部署（CPU only 可接受，GPU 可選）
- Python 3.10+ 運行環境
- 需考慮多用戶並發場景
- AutoML 訓練時間可能很長，需非同步處理
- CSV 大檔案傳輸需要優化



## Stakeholders

- 多個終端用戶（透過 Agent 互動）
- AI Agents（呼叫 MCP tools）
- 系統管理員（部署和維護）

