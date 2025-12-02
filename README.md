# AutoML MCP System

Multi-user AutoML system accessible via AI Agents through MCP (Model Context Protocol).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Custom Code (Maintained)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────┐      ┌──────────────────────────┐             │
│  │   AutoML MCP Server      │      │   AutoML API Service     │             │
│  │   (automl-mcp-server/)   │─────▶│   (automl-service/)      │             │
│  │                          │ HTTP │                          │             │
│  │   • FastMCP              │      │   • FastAPI + Pydantic   │             │
│  │   • MCP Tools for Agents │      │   • Job Queue (Redis)    │             │
│  │   • SSE/STDIO transport  │      │   • Dataset Management   │             │
│  │                          │      │   • DDD Architecture     │             │
│  │   Port: 8002             │      │   Port: 8001             │             │
│  └──────────────────────────┘      └───────────┬──────────────┘             │
│                                                │                             │
└────────────────────────────────────────────────┼─────────────────────────────┘
                                                 │ Redis Queue
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     External Services (Zero Maintenance)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────┐      ┌──────────────────────────┐             │
│  │   Redis                  │      │   AutoGluon Worker       │             │
│  │   (redis:7-alpine)       │      │   (autogluon/autogluon)  │             │
│  │                          │      │                          │             │
│  │   • Job Queue            │◀────▶│   • Official Docker image│             │
│  │   • Status Store         │      │   • Update: change tag   │             │
│  │                          │      │                          │             │
│  │   Port: 6379             │      │   • Pop job from Redis   │             │
│  └──────────────────────────┘      │   • Run AutoGluon train  │             │
│                                    │   • Save model to MinIO  │             │
│  ┌──────────────────────────┐      └──────────────────────────┘             │
│  │   MinIO                  │                 │                              │
│  │   (External Server)      │◀────────────────┘                              │
│  │                          │                                                │
│  │   • Dataset storage      │                                                │
│  │   • Model storage        │                                                │
│  └──────────────────────────┘                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Components

| Component | Directory | Purpose | Tech Stack |
|-----------|-----------|---------|------------|
| AutoML API | `automl-service/` | REST API for job/dataset management | FastAPI, Redis, DDD |
| AutoML MCP | `automl-mcp-server/` | MCP server for AI agents | FastMCP, httpx |
| AutoGluon Worker | `automl-worker/` | ML training execution | Official AutoGluon image |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- External MinIO server
- Python 3.10+ (for local development)

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your MinIO settings
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Connect AI Agent

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

## Usage Flow

```
User: "Train a model on my dataset to predict 'outcome'"

Agent:
1. register_dataset(minio_path="bucket/data.csv")
   → dataset_id

2. submit_automl_job(dataset_id, target="outcome", problem_type="binary")
   → job_id (returns immediately!)

3. "Training started. I'll check progress..."

4. get_job_status(job_id)  [poll until complete]
   → status: "completed", model_id

5. get_model_leaderboard(model_id)
   → Show results to user

6. predict(model_id, new_dataset_id)
   → Predictions
```

## Update AutoGluon

Just change the tag in `automl-worker/Dockerfile`:

```dockerfile
FROM autogluon/autogluon:1.3.0-cpu-py3.10  # Update version here
```

Then rebuild:
```bash
docker-compose build automl-worker
docker-compose up -d automl-worker
```

## Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r automl-service/requirements.txt
pip install -r automl-mcp-server/requirements.txt

# Run API locally
cd automl-service && uvicorn src.main:app --reload

# Run MCP server locally (STDIO mode)
cd automl-mcp-server && python -m src.main
```

## Project Structure

```
workspace251202/
├── automl-service/          # REST API Service
│   ├── src/
│   │   ├── domain/          # DDD Domain Layer
│   │   ├── application/     # Use Cases
│   │   ├── infrastructure/  # Redis, MinIO, etc.
│   │   └── interface/       # FastAPI Routes
│   ├── Dockerfile
│   └── requirements.txt
│
├── automl-mcp-server/       # MCP Server
│   ├── src/
│   │   └── infrastructure/mcp/
│   │       ├── handlers/    # MCP Tool Handlers
│   │       ├── client.py    # HTTP Client
│   │       └── server.py    # FastMCP Server
│   ├── Dockerfile
│   └── requirements.txt
│
├── automl-worker/           # AutoGluon Worker
│   ├── src/worker.py        # Job Consumer
│   └── Dockerfile           # Uses official AutoGluon image
│
├── docker-compose.yml       # Full stack deployment
├── .env.example             # Environment template
└── .vscode/mcp.json         # VS Code MCP config
```

## License

MIT
