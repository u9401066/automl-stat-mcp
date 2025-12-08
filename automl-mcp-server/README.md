# AutoML MCP Server

MCP Server for AutoML capabilities, enabling AI Agents to train and compare ML models.

## Features

- **Non-blocking Training**: Training jobs run in background, MCP calls return immediately
- **Multiple Training Modes**: AutoML, specific algorithms, algorithm comparison
- **Job Status Tracking**: Poll for progress, get results when complete
- **Model Management**: List models, view leaderboards, make predictions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       AI Agent                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ MCP Protocol
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   AutoML MCP Server                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  AutoMLHandler                                       │    │
│  │  ├── register_dataset()    ← Returns immediately     │    │
│  │  ├── submit_automl_job()   ← Returns job_id (async!) │    │
│  │  ├── get_job_status()      ← Poll for progress       │    │
│  │  ├── get_model_leaderboard()                         │    │
│  │  └── predict()                                       │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   AutoML Service                             │
│                   (Docker container)                         │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │   Job Worker    │  │   AutoGluon     │                   │
│  │  (background)   │  │    Engine       │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- AutoML Service running (see automl-service/)
- MinIO for dataset storage

### Installation

```bash
cd automl-mcp-server
pip install -r requirements.txt
```

### Run MCP Server

```bash
# STDIO mode (for VS Code Copilot / Claude Desktop)
python -m src.infrastructure.mcp.server

# SSE mode (for remote access)
python -m src.infrastructure.mcp.server --transport sse --port 8002

# Development with MCP Inspector
pip install "mcp[cli]"
mcp dev src/infrastructure/mcp/server.py
```

### VS Code Copilot Configuration

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "automl-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "src.infrastructure.mcp.server"],
      "cwd": "${workspaceFolder}/automl-mcp-server"
    }
  }
}
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "automl": {
      "command": "python",
      "args": ["-m", "src.infrastructure.mcp.server"],
      "cwd": "/path/to/automl-mcp-server"
    }
  }
}
```

## MCP Tools

### Dataset Upload (NEW! 📤)
| Tool | Description |
|------|-------------|
| `list_available_files` | List files in mounted directories |
| `upload_dataset` | Upload dataset with storage mode selection |
| `get_upload_help` | Get upload instructions |

**Two Storage Modes:**

| Mode | Storage | Lifetime | Use Case | Returns |
|------|---------|----------|----------|---------|
| `temporary` | Redis | Expires with job | One-time analysis | `job_id` |
| `permanent` | MinIO | Until deleted | ML training, repeated analysis | `dataset_id` |

**Upload Workflow:**
```
Agent: "我來幫你上傳資料。請回答兩個問題："

Q1: "資料來源？"
    1. 📁 本地檔案 (sample_data, uploads)
    2. ☁️ MinIO 路徑

User: "本地檔案"

Agent: list_available_files()
       → breast_cancer.csv, iris.csv, ...

Q2: "儲存方式？"
    1. 🔄 暫存 (一次性分析)
    2. 💾 永久存檔 (ML 訓練用)

User: "永久存檔"

Agent: upload_dataset(
         name="breast_cancer",
         source_type="local",
         source_path="/data/sample_data/breast_cancer.csv",
         storage_mode="permanent"  # or "temporary"
       )
       → permanent: {"dataset_id": "abc123", ...}
       → temporary: {"job_id": "job456", ...}
```

> ⚠️ **Important**: Copilot does NOT read file content. MCP Server reads files 
> directly from mounted volumes. This saves tokens and prevents truncation.

### Dataset Management
| Tool | Description |
|------|-------------|
| `register_dataset` | Register CSV from MinIO |
| `list_datasets` | List user's datasets |
| `delete_dataset` | Delete a dataset |

### Training (Async!)
| Tool | Description |
|------|-------------|
| `submit_automl_job` | Start AutoML training → returns job_id |
| `submit_specific_job` | Train specific algorithms |
| `submit_compare_job` | Compare multiple algorithms |

### Job Management
| Tool | Description |
|------|-------------|
| `get_job_status` | Check training progress |
| `list_jobs` | List all jobs |
| `cancel_job` | Cancel a job |

### Model Management
| Tool | Description |
|------|-------------|
| `list_models` | List trained models |
| `get_model_leaderboard` | View model comparison |
| `predict` | Make predictions |
| `delete_model` | Delete a model |

### Info
| Tool | Description |
|------|-------------|
| `list_algorithms` | Available algorithms |
| `health_check` | Service health |

## Usage Example (Agent Workflow)

```
User: "I have a dataset at minio://bucket/data.csv. Can you train a model to predict the 'outcome' column?"

Agent: 
1. register_dataset(name="my_data", minio_path="bucket/data.csv", user_id="user1")
   → {"dataset_id": "abc123", "columns": ["feature1", "feature2", "outcome"]}

2. submit_automl_job(dataset_id="abc123", target_column="outcome", problem_type="binary", user_id="user1")
   → {"job_id": "job456", "status": "pending"}

3. "I've started training your model. This may take a few minutes. I'll check the progress..."

4. get_job_status(job_id="job456", user_id="user1")
   → {"status": "running", "progress": 0.3}

5. "Training is 30% complete..."

6. get_job_status(job_id="job456", user_id="user1") 
   → {"status": "completed", "model_id": "model789"}

7. get_model_leaderboard(model_id="model789", user_id="user1")
   → [{"model_name": "WeightedEnsemble_L2", "score": 0.95}, ...]

8. "Training complete! The best model achieved 95% accuracy. Would you like me to make predictions?"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| AUTOML_SERVICE_URL | http://localhost:8001 | AutoML Service endpoint |
| HTTP_TIMEOUT | 30 | HTTP request timeout (seconds) |
| MCP_MODE | stdio | Transport mode |
| MCP_HOST | 0.0.0.0 | Host for SSE mode |
| MCP_PORT | 8002 | Port for SSE mode |
| LOG_LEVEL | INFO | Logging level |

## License

MIT
