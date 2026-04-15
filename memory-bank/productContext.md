# Product Context

## Overview

AutoML MCP System - 透過 MCP 讓 AI Agent 使用的自動機器學習與統計分析系統。

## 🎯 核心設計原則

**Agent 只負責四件事：**
1. **傳入檔案路徑** - 告訴系統資料在哪裡
2. **建立工單** - 設定要做什麼任務（含參數）
3. **查詢狀態** - 檢查工單執行進度
4. **取得結果連結** - 獲取輸出（模型/報告/圖片）

**系統內部負責所有其他事情：**
- ❌ Agent 不需要讀取檔案內容
- ❌ Agent 不需要計算統計數值
- ❌ Agent 不需要處理資料清理
- ❌ Agent 不需要管理模型訓練過程

## Core Features

- 🤖 AutoML 訓練 - 自動模型選擇 (AutoGluon)
- 📊 統計分析 - TableOne、EDA、自動分析
- 📁 檔案參考 - Agent 只傳路徑，系統處理一切
- 🔌 MCP 整合 - AI Agent 直接呼叫

## Technical Stack

- **Backend**: FastAPI, Redis, MinIO
- **ML Engine**: AutoGluon 1.3.1
- **Stats**: tableone, scipy, statsmodels, ydata-profiling
- **MCP**: FastMCP (SSE transport)
- **Deployment**: Docker Compose

## 標準工作流程

```
User: "用 titanic.csv 預測 survived"

Agent:
1. list_available_files() → 確認檔案存在
2. upload_dataset(file_path, name) → 取得 dataset_id
3. submit_automl_job(dataset_id, target) → 取得 job_id
4. get_job_status(job_id) → 等待完成
5. get_job_result(job_id) → 取得結果連結

Agent: "訓練完成！最佳模型達到 87% AUC。"
```

## 精簡工具清單

| 工具 | 用途 |
|------|------|
| `health_check` | 服務健康檢查 |
| `list_available_files` | 列出可用檔案 |
| `upload_dataset` | 註冊資料集 → dataset_id |
| `submit_automl_job` | ML 訓練工單 → job_id |
| `submit_tableone_job` | 統計分析工單 → job_id |
| `get_job_status` | 查詢工單狀態 |
| `get_stats_job_result` | 取得統計結果 |
| `get_model_leaderboard` | 取得模型排行 |

## 架構

```
AI Agent
   │
   ▼ (只傳路徑+建工單+查狀態+拿結果)
MCP Server (8002)
   │
   ├─→ AutoML Service (8001) → AutoML Worker
   │
   └─→ Stats Service (8003) → Stats Worker
                │
                ▼
        Redis + MinIO
```
多用戶 AutoML 服務系統，透過 MCP Server 暴露 AutoML 功能給 AI Agents 使用。Agents 代表用戶上傳資料、訓練模型、執行預測，並將結果返回給用戶進行討論。



## Architecture

Microservices: MCP Server (8002) → AutoML Service (8001) + Stats Service (8003) → Workers → Redis + MinIO



DDD (Domain-Driven Design) with layers: Domain (stats-worker/tasks), Application (services), Infrastructure (MCP handlers). 83 MCP tools across AutoML (23) and Statistics (57) domains. Code quality issues: 11 files >500 lines requiring refactoring.



Clean Architecture with DDD + MCP Orchestration Layer - Domain (核心業務), Application (用例), Infrastructure (外部服務), Interface (API/MCP), MCP Orchestration (智能工具封裝)



Clean Architecture with DDD - Domain Layer (\u6838\u5fc3\u696d\u52d9\u908f\u8f2f), Application Layer (\u7528\u4f8b\u7de8\u6392), Infrastructure Layer (\u5916\u90e8\u670d\u52d9\u6574\u5408), Interface Layer (API/MCP \u7aef\u9ede)



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

- Python 3.11
- FastAPI
- MCP (Model Context Protocol)
- Docker Compose
- AutoGluon 1.3.1
- Redis
- MinIO



- Python 3.10+
- FastAPI
- FastMCP
- Docker
- Redis
- MinIO
- AutoGluon 1.3.1



- Python 3.11
- FastAPI
- AutoGluon 1.3.1
- Redis 7
- MinIO
- Docker
- MCP SSE Transport
- FastMCP



- Python 3.11
- FastAPI
- AutoGluon 1.3.1
- Redis (Job Queue)
- MinIO (S3-compatible Storage)
- Docker
- MCP SSE Transport



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

- scipy
- statsmodels
- lifelines
- tableone
- ydata-profiling
- matplotlib
- seaborn
- statannotations
- httpx
- celery
- pandas
- numpy



**統計分析:**
- tableone - Table 1 生成
- scipy - 統計檢定
- statsmodels - 進階統計模型
- lifelines - 生存分析
- scikit-learn - 機器學習工具
- numpy, pandas - 資料處理
- ydata-profiling - EDA 報告

**視覺化 (Phase 8 新增):**
- matplotlib>=3.7.0 - 基礎繪圖
- seaborn - 統計視覺化
- shap - SHAP 圖表（可選）

**AutoML:**
- autogluon.tabular==1.3.1 - AutoML 引擎

**基礎設施:**
- fastapi, uvicorn - API 服務
- redis - 任務佇列
- minio - 物件儲存
- mcp, fastmcp - MCP 協議


## 結果儲存 (Phase 8 新增)

分析任務完成後，結果同時儲存到：

1. **MinIO (雲端)** - API 存取、備份
2. **本地目錄 (新增)** - 使用者直接瀏覽

本地目錄結構：
```
/results/{user_id}/{job_name}_{timestamp}/
├── metadata.json    # 任務資訊
├── report.json      # 分析結果
├── report.html      # HTML 報告
├── figures/         # 圖表 PNG
└── data/            # 來源追蹤
```

存取方式：
- 直接瀏覽檔案系統：`./results/eric/roc_analysis_20241210/`
- 瀏覽器開啟 HTML 報告
- 複製圖表到簡報
- pydantic
- python-multipart



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



## Project Description

AutoML MCP System - Multi-user AutoML and statistical analysis platform accessible via AI Agents through MCP protocol

[2026-04-14 23:32:15] - 專案安全模型補充：Agent/Service 的本地檔案存取只允許 sample_data、projects、uploads 與暫存目錄，避免任意容器檔案暴露給 MCP 工具或 API。
