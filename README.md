# AutoML MCP System

Multi-user AutoML system accessible via AI Agents through MCP (Model Context Protocol).

**Features:**
- 🤖 **AutoML Training** - Automatic model selection with AutoGluon
- 📊 **Smart Statistical Analysis** - Intelligent auto-analysis with automatic method selection
- 📁 **Simple File References** - Agent only passes file paths, system handles everything
- 🔌 **MCP Integration** - Direct access from AI Agents (Claude, Copilot)
- 🔒 **Enterprise Ready** - HTTPS, POST-only API, multi-user isolation

## 🎯 Design Philosophy

**Agent 只負責四件事：**
1. **傳入檔案路徑** - 告訴系統資料在哪裡
2. **建立工單** - 設定要做什麼任務（含參數）
3. **查詢狀態** - 檢查工單執行進度
4. **取得結果連結** - 獲取輸出（模型/報告/圖片）

**系統內部負責所有其他事情** - 資料讀取、清理、訓練、評估、報告生成。

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Agent Workflow](docs/AGENT_WORKFLOW.md) | **Agent 工作流程與工具使用指南** |
| [MCP Tools Inventory](docs/MCP_TOOLS_INVENTORY.md) | 工具清單與狀態 |
| [Deployment Guide](docs/deployment-guide.md) | 完整部署教學 |
| [ROADMAP](docs/ROADMAP.md) | 開發藍圖與進度追蹤 |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent (Claude/Copilot)                       │
│                                                                              │
│   Agent 只做:  1. 傳檔案路徑  2. 建立工單  3. 查狀態  4. 拿結果連結          │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │ MCP Protocol
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server (8002)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     Core Tools (精簡工具集)                          │    │
│  │  • list_available_files    • submit_ml_job    • get_job_status      │    │
│  │  • submit_stats_job        • get_job_result   • health_check        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────┬────────────────────────────────────────┬─────────────────┘
                   │                                        │
                   ▼                                        ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│        AutoML Service            │    │        Stats Service             │
│  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │
│  │ 系統內部處理 (Agent 不管)  │  │    │  │ 系統內部處理 (Agent 不管)  │  │
│  │ • 資料讀取、驗證、清理     │  │    │  │ • 統計計算、假設檢定       │  │
│  │ • 特徵工程、編碼           │  │    │  │ • 表格生成、圖表繪製       │  │
│  │ • 模型訓練、調參、評估     │  │    │  │ • 報告產出                 │  │
│  └────────────────────────────┘  │    │  └────────────────────────────┘  │
└──────────────────┬───────────────┘    └──────────────────┬───────────────┘
                   │                                        │
                   ▼                                        ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│        AutoML Worker             │    │        Stats Worker              │
│  • AutoGluon 1.3.1               │    │  • ydata-profiling               │
│  • Model training                │    │  • tableone, scipy, statsmodels  │
└──────────────────────────────────┘    └──────────────────────────────────┘
                   │                                        │
                   └──────────────┬─────────────────────────┘
                                  ▼
               ┌──────────────────────────────────┐
               │     Shared Infrastructure        │
               │  ┌────────┐    ┌────────┐       │
               │  │ Redis  │    │ MinIO  │       │
               │  │ (6379) │    │ (9000) │       │
               │  └────────┘    └────────┘       │
               └──────────────────────────────────┘
```

## 🔄 Standard Workflow

```
User: "用 titanic.csv 預測 survived"

Agent:
1. list_available_files() → 確認檔案存在
2. submit_ml_job(file_path="/data/sample_data/titanic.csv", target="survived")
   → job_id
3. get_job_status(job_id) → 等待完成
4. get_job_result(job_id) → 取得模型和報告連結

Agent: "訓練完成！最佳模型達到 87% AUC。"
```

## ⛔ Agent Should NOT Do

| Wrong | Right |
|-------|-------|
| 用 `cat` 讀取 CSV 內容 | 只傳入檔案路徑 |
| 自己計算統計數值 | 建立統計工單讓系統算 |
| 解析 CSV 判斷欄位類型 | 系統自動判斷 |
| 呼叫多個底層工具串接 | 用高階工單一次搞定 |

## Components

| Component | Directory | Purpose | Tech Stack | Status |
|-----------|-----------|---------|------------|--------|
| AutoML API | `automl-service/` | REST API for job/dataset management | FastAPI, Redis, DDD | ✅ Ready |
| AutoML MCP | `automl-mcp-server/` | MCP server for AI agents | FastMCP, httpx | ✅ Ready |
| AutoML Worker | `automl-worker/` | ML training execution | AutoGluon 1.3.1 | ✅ Ready |
| Stats API | `stats-service/` | Statistical analysis API + **Data Cleaning** | FastAPI, Redis | ✅ Ready |
| Stats Worker | `stats-worker/` | EDA, TableOne, ROC, Survival analysis | ydata-profiling, tableone, lifelines | ✅ Ready |

## 📁 Directory Structure

```
workspace/
├── datasets/              # 原始資料 (read-only)
├── processed/             # 處理過的資料
│   └── {user_id}/
│       ├── data_20251210.csv
│       └── data_20251210_metadata.json
├── results/               # 📊 分析結果 (User 可直接查看)
│   └── {user_id}/
│       └── {job_name}_{timestamp}/
│           ├── metadata.json      # Job 資訊
│           ├── report.json        # 分析結果
│           ├── report.html        # 📄 HTML 報告
│           ├── figures/           # 📈 視覺化圖表
│           │   ├── roc_curve.png
│           │   ├── feature_importance.png
│           │   └── ...
│           └── data/
│               └── source_info.json  # 資料來源資訊
├── sample_data/           # 範例資料集
└── uploads/               # 上傳的檔案
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- External MinIO server (or modify to use local MinIO)

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

Example `.env`:
```bash
# Your MinIO server address
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=false
```

### 2. Start All Services (One Command!)

```bash
docker compose up -d
```

This starts:
- **Redis** - Job queue (port 6379)
- **AutoML API** - REST API (port 8001)
- **AutoML MCP** - MCP Server for AI agents (port 8002)
- **Stats API** - Statistical analysis API (port 8003)
- **4x AutoML Workers** - Parallel training execution
- **2x Stats Workers** - Statistical analysis execution

### 3. Verify Services

```bash
# Check running containers
docker ps

# Check API health
curl http://localhost:8001/health
# {"status":"healthy","version":"1.0.0"}
```

### 4. Connect AI Agent

For VS Code Copilot, the MCP config is in `.vscode/mcp.json`.

For Claude Desktop, add to config:
```json
{
  "mcpServers": {
    "automl": {
      "type": "sse",
      "url": "http://localhost:8002/sse"
    }
  }
}
```

## 📊 Current MCP Tools

### Core Tools (Recommended)

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `health_check` | 服務健康檢查 | - | status |
| `list_available_files` | 列出可用檔案 | directory | files[] |
| `upload_dataset` | 註冊資料集 | file_path, name | dataset_id |
| `submit_automl_job` | ML 訓練工單 | dataset_id, target | job_id |
| `submit_tableone_job` | 統計分析工單 | dataset_id, settings | job_id |
| `convert_to_binary` | 轉換欄位為 0/1 | csv_path, column, mapping | output_path |
| `handle_missing_values` | 缺失值處理 | csv_path, strategy | output_path |
| `get_column_info` | 取得欄位資訊 | csv_path | column_info |
| `get_job_status` | 查詢工單狀態 | job_id | status, progress |
| `get_stats_job_result` | 取得統計結果 | job_id | result |
| `get_model_leaderboard` | 取得模型排行 | model_id | leaderboard |

### Note on Other Tools

Many other tools exist but require refactoring to follow the simplified workflow.
See [MCP Tools Inventory](docs/MCP_TOOLS_INVENTORY.md) for full status.

## Development

### Run Tests

```bash
# E2E tests
cd tests && pip install -r requirements.txt
pytest test_e2e.py -v

# Stats worker tests
cd stats-worker && pytest tests/ -v
```

### View Logs

```bash
# All logs
docker compose logs -f

# Specific service
docker compose logs -f automl-api
docker compose logs -f stats-worker
```

## License

MIT
