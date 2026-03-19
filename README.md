# AutoML Stat MCP

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)

**AI-powered statistical analysis and AutoML platform using Model Context Protocol (MCP).**

AutoML Stat MCP provides 51+ statistical and machine learning tools through the MCP interface, enabling AI agents (Claude, GPT, etc.) to perform comprehensive clinical research analysis. Supports **real-time progress notifications** via SSE for long-running operations.

---

## ✨ Features

### 📊 Statistical Analysis (51+ MCP Tools)
- **Descriptive Statistics**: Table One generation, correlation analysis, group comparisons
- **Survival Analysis**: Kaplan-Meier curves, Cox proportional hazards, log-rank tests
- **Propensity Score Analysis**: PSM matching, IPW weighting, treatment effect estimation
- **ROC Analysis**: AUC with CI, threshold optimization, DeLong test for model comparison
- **Power Analysis**: T-test, ANOVA, Chi-square, proportion, survival sample size calculation

### 🤖 Machine Learning (AutoGluon Backend)
- **AutoML Training**: Automatic model selection and hyperparameter tuning
- **Multi-Algorithm Support**: XGBoost, LightGBM, CatBoost, Random Forest, Neural Networks
- **Classification & Regression**: Binary, multiclass, and regression problems

### 🔧 Data Preparation
- **Missing Value Analysis**: MCAR/MAR/MNAR detection with imputation recommendations
- **Data Cleaning**: PII detection, outlier handling, encoding categorical variables
- **Quality Checks**: VIF multicollinearity, data validation, integrity checks

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM recommended
- (Optional) GPU for accelerated ML training

### ⚡ One-Line Install (推薦)

```bash
# Clone and auto-install
git clone https://github.com/u9401066/automl-stat-mcp.git
cd automl-stat-mcp
./quick-install.sh
```

### 🎯 Quick Launch Scripts

```bash
# 方式 1: 使用啟動腳本 (推薦)
./start.sh           # 預設模式 (統計分析)
./start.sh ml        # ML 模式 (含訓練)
./start.sh full      # 完整模式 (含 MinIO)

# 方式 2: 使用 Makefile (最方便)
make start           # 啟動預設服務
make start-ml        # 啟動 ML 服務
make start-full      # 啟動完整服務
make logs            # 查看日誌
make health          # 健康檢查
make help            # 所有可用指令

# 方式 3: 使用 Docker Compose (進階)
docker compose up -d                    # 預設
docker compose --profile ml up -d       # ML
docker compose --profile full up -d     # 完整
```

### 🛑 Stop Services

```bash
./stop.sh            # 或 make stop
```

### Verify Installation

```bash
# Check service health
curl http://localhost:8003/health  # Stats service
curl http://localhost:8002/health  # MCP server

# List available sample datasets
curl http://localhost:8003/api/files/list
```

### Connect to AI Agent

#### VS Code Copilot (推薦)

在你的專案根目錄建立 `.vscode/mcp.json`：

```json
{
  "servers": {
    "automl-stat-mcp": {
      "url": "http://localhost:8002/sse",
      "type": "sse"
    }
  }
}
```

或使用快速設定腳本，在目標專案目錄執行：

```bash
/path/to/automl-stat-mcp/scripts/setup-vscode-mcp.sh
```

#### Claude Desktop / Cursor

在 MCP 設定中新增：

```json
{
  "mcpServers": {
    "automl-stat-mcp": {
      "url": "http://localhost:8002/sse"
    }
  }
}
```

---

## 📊 Deployment Profiles

| Profile | Command | Components | Use Case |
|---------|---------|------------|----------|
| Default | `docker compose up -d` | Stats + MCP | Statistical analysis only |
| `ml` | `docker compose --profile ml up -d` | + AutoML API/Workers | ML training enabled |
| `full` | `docker compose --profile full up -d` | + MinIO | Full stack with object storage |

### Storage Modes

**Default**: Local file storage (no external dependencies)

| Mode | Environment Variable | Description | Requirements |
|------|---------------------|-------------|-------------|
| **Local** (Default) | `STORAGE_MODE=local` | Uses local `/data` directory for all storage operations | None |
| **MinIO** | `STORAGE_MODE=minio` | S3-compatible object storage for distributed deployment | Profile: `full` |

**Volume Mounts**:
```yaml
volumes:
  - ./sample_data:/data/sample_data:ro   # Sample datasets (read-only)
  - ./projects:/data/projects             # User projects
  - local-results:/data/results           # Analysis results
```

**Switching Storage Modes**:
```bash
# Local storage (default)
docker compose up -d

# MinIO storage (requires full profile)
STORAGE_MODE=minio docker compose --profile full up -d
```

**Path Resolution**:
- User input: `iris.csv` → Container path: `/data/sample_data/iris.csv`
- User input: `projects/study1/data.csv` → `/data/projects/study1/data.csv`

---

## 🛠️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_MODE` | `local` | Storage backend: `local` or `minio` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO server address |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |

### Scaling Workers

```bash
# Scale stats workers
docker compose up -d --scale stats-worker=4

# Scale ML workers (requires ml profile)
docker compose --profile ml up -d --scale automl-worker=8 --scale stats-worker=4
```

---

## 📁 Sample Datasets

The `sample_data/` directory includes test datasets:

| Dataset | Type | Target | Records |
|---------|------|--------|---------|
| `iris.csv` | Classification | species | 150 |
| `titanic.csv` | Binary | survived | 891 |
| `heart_disease.csv` | Binary | target | 303 |
| `breast_cancer.csv` | Binary | diagnosis | 569 |
| `medical_study_200.csv` | RCT | treatment_group | 200 |
| `rossi_recidivism.csv` | Survival | arrest, week | 432 |
| `stanford_heart.csv` | Survival | status, time | 103 |

---

## 🔧 MCP Tools Reference

### Quick Start Tools (Recommended)

| Tool | Description |
|------|-------------|
| `smart_analyze` | One-stop analysis: stats + Table One + correlations |
| `quick_preview` | Fast data preview with auto path resolution |
| `compare_treatment_groups` | Simplified group comparison |
| `analyze_medical_study` | Complete RCT analysis pipeline |

### Statistical Analysis

| Category | Tools |
|----------|-------|
| **Descriptive** | `generate_tableone_directly`, `analyze_correlations`, `compare_groups`, `get_quick_stats` |
| **Survival** | `kaplan_meier_survival`, `cox_proportional_hazards` |
| **Propensity** | `run_propensity_analysis`, `estimate_treatment_effect` |
| **ROC** | `compute_roc_curve`, `compare_roc_curves`, `find_optimal_threshold`, `full_classifier_evaluation` |
| **Power** | `power_ttest`, `power_anova`, `power_chisquare`, `power_proportion`, `power_survival` |

### Data Preparation

| Category | Tools |
|----------|-------|
| **Quality** | `analyze_missing_values`, `check_multicollinearity`, `get_column_info` |
| **Cleaning** | `handle_missing_values`, `encode_categorical`, `convert_to_binary`, `filter_rows`, `remove_columns` |
| **Project** | `create_project_workspace`, `list_available_files`, `list_project_workspaces` |

### ML Training (Requires `ml` profile)

| Tool | Description |
|------|-------------|
| `train_and_wait` | One-shot AutoML training |
| `submit_automl_job` | Async training submission |
| `get_job_status` | Check training progress |
| `get_model_leaderboard` | View trained models ranking |
| `predict` | Make predictions |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Agent (Claude/GPT)                       │
└─────────────────────────────────────────────────────────────────┘
                                │ MCP Protocol
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     automl-mcp (Port 8002)                      │
│                   51+ MCP Tools Handlers                        │
└─────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │   stats-service (8003)    │   │   automl-api (8001)       │
    │   Statistical Analysis    │   │   ML Training API         │
    └───────────────────────────┘   └───────────────────────────┘
                    │                           │
                    ▼                           ▼
    ┌───────────────────────────┐   ┌───────────────────────────┐
    │      stats-worker         │   │     automl-worker         │
    │   Background Analysis     │   │   AutoGluon Training      │
    └───────────────────────────┘   └───────────────────────────┘
                    │                           │
                    └───────────────┬───────────┘
                                    ▼
                    ┌───────────────────────────┐
                    │         Redis             │
                    │    Job Queue & Cache      │
                    └───────────────────────────┘
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
┌───────────────────────┐                     ┌───────────────────────┐
│   Local Storage       │         OR          │   MinIO Storage       │
│   /data/...           │                     │   Object Storage      │
└───────────────────────┘                     └───────────────────────┘
```

---

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [MCP Tools Inventory](docs/MCP_TOOLS_INVENTORY.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Testing Strategy](docs/TESTING_STRATEGY.md)
- [Roadmap](docs/ROADMAP.md)

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone your fork or local mirror
git clone --recursive https://github.com/YOUR_USERNAME/automl-stat-mcp.git
cd automl-stat-mcp

# Sync the workspace environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync --all-extras

# Install developer hooks
make hooks-install

# Run quality gates
make check

# Run tests (interactive mode)
./run_tests.sh

# Or use focused targets
make test        # smoke tests
make test-all    # full pytest collection

# Or run specific test suites
./run_tests.sh fast        # Fast tests only
./run_tests.sh edge        # Edge case tests
./run_tests.sh e2e         # End-to-end workflow tests
./run_tests.sh performance # Performance & load tests
./run_tests.sh security    # Security tests
./run_tests.sh coverage    # Generate coverage report
```

### Test Suites

Our comprehensive test coverage includes:

- **Edge Cases** (50+ tests): Data boundaries, input validation, statistical/ML edge cases
- **E2E Workflows** (20+ tests): Complete medical RCT, survival analysis, ML training pipelines
- **Performance** (15+ tests): Load benchmarks, concurrent requests, stress tests
- **Security** (20+ tests): Injection attacks, path traversal, rate limiting, user isolation

See [TESTING_ENHANCEMENT_PLAN.md](docs/TESTING_ENHANCEMENT_PLAN.md) for details.

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html tests/

# Run specific markers
uv run pytest -m "edge_case" tests/
uv run pytest -m "e2e" tests/
uv run pytest -m "performance" tests/
uv run pytest -m "security" tests/
```

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with these excellent open source projects:

- [AutoGluon](https://auto.gluon.ai/) - AutoML framework
- [lifelines](https://lifelines.readthedocs.io/) - Survival analysis
- [tableone](https://github.com/tompollard/tableone) - Clinical table generation
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) - AI agent protocol

---

## 📧 Contact

- Use the repository Issues tab for bug reports and regressions.
- Use the repository Discussions tab for design questions and workflow proposals.
