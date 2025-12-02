# Product Context

Describe the product.

## Overview

Provide a high-level overview of the project.

## Core Features

- Feature 1
- Feature 2

## Technical Stack

- Tech 1
- Tech 2

## Project Description

Multi-user AutoML system accessible via AI Agents through MCP. Users can submit ML training jobs, compare algorithms, and make predictions through natural language with AI agents.



多用戶 AutoML + 統計分析服務系統。
- AutoML：使用 AutoGluon（Python），支援自動搜索、指定算法、比較算法
- 統計分析：使用 tableone + pingouin + ydata-profiling
- 兩個獨立 Docker 服務 + 兩個 MCP Server
- Agent 上傳檔案到 MinIO，MCP Server 驗證並轉發請求
- 非同步任務 + WebSocket 推送結果
- User/Session 資源隔離



多用戶 AutoML 服務系統。Agent 上傳檔案到 MinIO，透過 MCP Server 呼叫 AutoML 訓練和預測。支援非同步訓練 + WebSocket 進度推送，User/Session 資源隔離。



多用戶 AutoML 服務系統，透過 MCP Server 暴露 AutoML 功能給 AI Agents 使用。Agents 代表用戶上傳資料、訓練模型、執行預測，並將結果返回給用戶進行討論。



## Architecture

Separated Container Architecture with 4 components: 1) AutoML API (FastAPI) - lightweight REST API handling job/dataset management via Redis queue, 2) AutoML MCP Server (FastMCP) - exposes MCP tools for AI agents, 3) AutoGluon Worker (official image) - pulls jobs from Redis and runs training, 4) External services: Redis (job queue) + MinIO (file storage). Key design: API container has NO AutoGluon installed, training delegated to worker containers.



## 系統架構（最終版）

```
┌─────────────────────────────────────────────────────────┐
│                    使用者 + Agents                       │
└─────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │   Agent 1   │ │   Agent 2   │ │   Agent N   │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           │ 上傳檔案到 MinIO              │
           ▼               ▼               ▼
    ┌─────────────────────────────────────────────────────┐
    │                      MinIO                          │
    └─────────────────────────────────────────────────────┘
           │
           │ minio_url
           ▼
    ┌─────────────────────────────────────────────────────┐
    │              MCP Servers (分開部署)                  │
    │  ┌───────────────────┐  ┌───────────────────┐       │
    │  │ AutoML MCP Server │  │ Stats MCP Server  │       │
    │  │ (Python)          │  │ (Python)          │       │
    │  └─────────┬─────────┘  └─────────┬─────────┘       │
    └────────────┼────────────────────────┼───────────────┘
                 │                        │
                 │ HTTP + WebSocket       │ HTTP
                 ▼                        ▼
    ┌─────────────────────┐  ┌─────────────────────┐
    │ AutoGluon Docker    │  │ Stats Docker        │
    │ + FastAPI           │  │ + FastAPI           │
    │ ─────────────────── │  │ ─────────────────── │
    │ • AutoML 搜索       │  │ • tableone          │
    │ • 指定算法訓練      │  │ • pingouin          │
    │ • 比較算法          │  │ • ydata-profiling   │
    │ • Leaderboard       │  │ • lifelines         │
    │ • 預測              │  │                     │
    └─────────────────────┘  └─────────────────────┘
```

### AutoML API Endpoints

**資料集管理**
- POST /datasets/register - 註冊 MinIO 檔案
- GET /datasets - 列出用戶資料集
- DELETE /datasets/{id} - 刪除資料集

**訓練任務**
- POST /train/automl - AutoML 自動搜索
- POST /train/specific - 指定算法訓練
- POST /train/compare - 比較多個算法
- GET /jobs/{job_id} - 查詢任務狀態
- DELETE /jobs/{job_id} - 取消任務
- WebSocket /ws/jobs/{job_id} - 進度推送

**模型管理**
- GET /models - 列出模型
- GET /models/{id}/leaderboard - 取得排行榜
- GET /models/{id}/importance - 特徵重要性
- DELETE /models/{id} - 刪除模型

**預測**
- POST /predict - 執行預測

### Stats API Endpoints
- POST /stats/table1 - 生成 Table 1
- POST /stats/test - 統計檢定
- POST /stats/eda - EDA 報告
- POST /stats/survival - 存活分析



## 系統架構（更新版）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User 1    │     │   User 2    │     │   User N    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent 1   │     │   Agent 2   │     │   Agent N   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ 上傳檔案          │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────┐
│                      MinIO                          │
│              (Object Storage)                       │
└─────────────────────────────────────────────────────┘
       │ 
       │ minio_url
       ▼
┌─────────────────────────────────────────────────────┐
│                   MCP Server                        │
│  Tools: register_dataset, automl_train,             │
│         automl_predict, list_models, ...            │
│  (傳遞 user_id/session_id)                          │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP + WebSocket
                       ▼
┌─────────────────────────────────────────────────────┐
│                 AutoML Server                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │Dataset Store│  │ Job Manager │  │Model Registry│ │
│  │(MinIO refs) │  │ (async+WS)  │  │(user isolated)│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│  ┌─────────────────────────────────────────────────┐│
│  │              AutoML Engine (FLAML)              ││
│  └─────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────┘
```

### API Endpoints (更新)

**資料集管理**
- POST /datasets/register - 註冊 MinIO 檔案為資料集
- GET /datasets - 列出用戶的資料集
- DELETE /datasets/{id} - 刪除資料集

**訓練任務**
- POST /automl/train - 提交訓練任務（返回 job_id）
- GET /jobs/{job_id} - 查詢任務狀態
- DELETE /jobs/{job_id} - 取消任務
- WebSocket /ws/jobs/{job_id} - 接收進度推送

**模型管理**
- GET /models - 列出用戶的模型
- DELETE /models/{id} - 刪除模型

**預測**
- POST /automl/predict - 執行預測（同步）



三層架構：
1. AutoML Server (FastAPI) - HTTP API 層
   - POST /datasets/upload - 上傳資料集
   - POST /automl/train - 訓練模型
   - POST /automl/predict - 執行預測
   
2. Core Library - 核心業務邏輯
   - dataset_store: 資料集存儲管理
   - automl_engine: AutoML 訓練邏輯（FLAML/auto-sklearn）
   - model_registry: 模型持久化和元數據管理
   - schemas: Pydantic 資料模型
   
3. MCP Server - Agent 介面層
   - 將 HTTP API 包裝為 MCP tools
   - Tools: upload_dataset, automl_train, automl_predict
   - 處理 Agent 請求並轉發到 AutoML Server



## Technologies

- Python 3.10+
- FastAPI
- FastMCP
- Redis
- Docker
- AutoGluon (official image)
- MinIO



- Python 3.10+
- AutoGluon (AutoML)
- FastAPI
- Pydantic v2
- Docker
- MinIO
- WebSocket
- MCP (Model Context Protocol)



- Python 3.10+
- FastAPI
- Pydantic v2
- FLAML (AutoML)
- MCP (Model Context Protocol)
- WebSocket
- MinIO (Object Storage)
- httpx (async HTTP)
- uvicorn (ASGI)
- joblib
- pandas
- scikit-learn



- Python 3.10+
- FastAPI
- Pydantic v2
- FLAML (AutoML backend)
- MCP (Model Context Protocol)
- httpx (async HTTP client)
- uvicorn (ASGI server)
- joblib (model serialization)
- pandas
- scikit-learn



## Libraries and Dependencies

- fastapi
- uvicorn
- pydantic v2
- mcp
- httpx
- redis
- minio
- pandas



- autogluon.tabular
- fastapi
- uvicorn
- pydantic>=2
- pandas
- numpy
- minio
- websockets
- httpx
- tableone
- pingouin
- ydata-profiling
- lifelines
- mcp



- fastapi
- uvicorn
- pydantic>=2
- pandas
- numpy
- joblib
- flaml
- scikit-learn
- httpx
- websockets
- minio
- mcp (Python SDK)
- asyncio



- fastapi
- uvicorn
- pydantic>=2
- pandas
- numpy
- joblib
- flaml
- scikit-learn
- httpx
- mcp (Python SDK)

