# AutoML MCP System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)

Multi-user AutoML system accessible via AI Agents through MCP (Model Context Protocol).

## ✨ Features

- 🤖 **AutoML Training** - Automatic model selection with AutoGluon
- 📊 **Statistical Analysis** - Comprehensive stats tools (TableOne, ROC, Survival, Power)
- 📁 **Simple File References** - Agent passes file paths, system handles everything
- 💾 **Result Persistence** - All results saved to Redis + MinIO with unique IDs
- 🔌 **MCP Integration** - Direct access from AI Agents (Claude, Copilot)
- 🔒 **Enterprise Ready** - HTTPS, multi-user isolation

## 🎯 Design Philosophy

**Agent 只負責四件事：**
1. **傳入檔案路徑** - 告訴系統資料在哪裡
2. **建立工單** - 設定要做什麼任務（含參數）
3. **查詢狀態** - 檢查工單執行進度
4. **取得結果** - 獲取輸出（模型/報告/圖片 + 持久化連結）

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Agent Workflow](docs/AGENT_WORKFLOW.md) | Agent 工作流程與工具使用指南 |
| [Architecture](docs/ARCHITECTURE.md) | 系統架構設計 |
| [MCP Tools Inventory](docs/MCP_TOOLS_INVENTORY.md) | 工具清單與狀態 |
| [Deployment Guide](docs/deployment-guide.md) | 完整部署教學 |
| [Roadmap](docs/ROADMAP.md) | 開發藍圖與進度追蹤 |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent (Claude/Copilot)                       │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │ MCP Protocol (SSE)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Server (Port 8002)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        98+ MCP Tools                                 │    │
│  │  AutoML (26) | Stats (57+) | Cleaning (9) | Workflow (3)            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└──────────────────┬────────────────────────────────────────┬─────────────────┘
                   │                                        │
                   ▼                                        ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│        AutoML Service (8001)     │    │        Stats Service (8003)      │
│  • Dataset Management            │    │  • Statistical Analysis          │
│  • Job Orchestration             │    │  • Data Cleaning                 │
│  • Model Registry                │    │  • Result Storage API            │
└──────────────────┬───────────────┘    └──────────────────┬───────────────┘
                   │                                        │
                   ▼                                        ▼
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│        AutoML Worker             │    │        Stats Worker              │
│  • AutoGluon 1.3.1               │    │  • ydata-profiling, tableone     │
│  • Model training                │    │  • lifelines, scipy, statsmodels │
└──────────────────────────────────┘    └──────────────────────────────────┘
                   │                                        │
                   └──────────────┬─────────────────────────┘
                                  ▼
               ┌──────────────────────────────────────┐
               │     Shared Infrastructure            │
               │  ┌────────┐    ┌────────┐           │
               │  │ Redis  │    │ (9000) │           │
               │  │ (6379) │    │ MinIO  │           │
               │  └────────┘    └────────┘           │
               │    Cache         Object              │
               │    Queue         Storage             │
               └──────────────────────────────────────┘
```

## 📁 Directory Structure

```
workspace/
├── automl-mcp-server/    # MCP Server for AI Agents
├── automl-service/       # AutoML REST API
├── automl-worker/        # ML Training Workers
├── stats-service/        # Statistics REST API
├── stats-worker/         # Statistics Workers
├── docs/                 # Documentation
│   ├── design-issues/    # Design decisions
│   └── archive/          # Completed plans
├── memory-bank/          # Project context (for AI agents)
├── projects/             # User research projects
├── sample_data/          # Sample datasets
└── docker-compose.yml    # Main deployment
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- MinIO server (external or local)

### 1. Configure Environment

```bash
cp .env.example .env
nano .env
```

Required settings:
```bash
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
```

### 2. Start All Services

```bash
docker compose up -d
```

Services started:
- **Redis** (6379) - Job queue
- **AutoML API** (8001) - REST API
- **AutoML MCP** (8002) - MCP Server
- **Stats API** (8003) - Statistics API
- **4x AutoML Workers** - ML training
- **2x Stats Workers** - Statistical analysis

### 3. Verify

```bash
docker ps
curl http://localhost:8001/health
```

### 4. Connect AI Agent

**VS Code Copilot**: See `.vscode/mcp.json`

**Claude Desktop**:
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

## 📊 Key MCP Tools

| Category | Tools | Description |
|----------|-------|-------------|
| **File** | `list_available_files`, `upload_dataset` | 檔案管理 |
| **AutoML** | `submit_automl_job`, `train_and_wait`, `predict` | ML 訓練 |
| **Stats** | `compare_groups`, `analyze_correlations`, `generate_tableone_directly` | 統計分析 |
| **Cleaning** | `handle_missing_values`, `convert_to_binary` | 資料清理 |
| **ROC** | `compute_roc_curve`, `full_classifier_evaluation` | 分類評估 |
| **Survival** | `kaplan_meier_survival`, `cox_proportional_hazards` | 存活分析 |
| **Power** | `calculate_ttest_sample_size`, `calculate_survival_sample_size` | 樣本數 |

See [MCP Tools Inventory](docs/MCP_TOOLS_INVENTORY.md) for complete list (98+ tools).

## 🆕 Recent Updates (Dec 2025)

- **Result Persistence**: Analysis results saved to Redis + MinIO with `result_id`
- **Visualization (Phase 8)**: Publication-quality charts (ROC, KM, SHAP)
- **Data Cleaning**: 9 preprocessing tools
- **Local Results**: `/results/{user_id}/` with HTML reports

## 🔧 Development

```bash
# E2E tests
cd tests && pytest test_e2e.py -v

# Stats worker tests  
cd stats-worker && pytest tests/ -v

# View logs
docker compose logs -f automl-mcp
```

## 📄 License

MIT
