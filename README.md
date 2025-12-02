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

- Docker
- External MinIO server (or modify to use local MinIO)
- Python 3.10+ (for local development)

### 1. Configure Environment

```bash
# Edit .env with your MinIO credentials
nano .env
```

Example `.env`:
```bash
MINIO_ENDPOINT=192.168.1.102:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=false
```

### 2. Create Docker Network

```bash
docker network create automl-network
```

### 3. Start Services

```bash
# Start Redis
docker run -d --name automl-redis --network automl-network -p 6379:6379 redis:7-alpine

# Build and start API
docker build -t automl-api ./automl-service
docker run -d --name automl-api --network automl-network -p 8001:8001 \
  -e REDIS_HOST=automl-redis \
  -e MINIO_ENDPOINT=$MINIO_ENDPOINT \
  -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY \
  -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY \
  automl-api

# Build and start MCP Server
docker build -t automl-mcp ./automl-mcp-server
docker run -d --name automl-mcp --network automl-network -p 8002:8002 \
  -e AUTOML_SERVICE_URL=http://automl-api:8001 \
  automl-mcp

# Build and start Worker
docker build -t automl-worker ./automl-worker
docker run -d --name automl-worker --network automl-network \
  -e REDIS_HOST=automl-redis \
  -e MINIO_ENDPOINT=$MINIO_ENDPOINT \
  -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY \
  -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY \
  automl-worker
```

### 4. Verify Services

```bash
# Check API health
curl http://localhost:8001/health
# {"status":"healthy","version":"1.0.0"}

# Check available algorithms
curl http://localhost:8001/algorithms
```

### 5. Connect AI Agent

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
# Available tags: https://hub.docker.com/r/autogluon/autogluon/tags
FROM autogluon/autogluon:1.3.1-cpu-framework-ubuntu22.04-py3.11  # Current
# For GPU: autogluon/autogluon:1.3.1-cuda12.4-framework-ubuntu22.04-py3.11
```

Then rebuild:
```bash
docker build -t automl-worker ./automl-worker
docker rm -f automl-worker
docker run -d --name automl-worker ... automl-worker  # Same run command as above
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/datasets/register` | Register CSV from MinIO |
| GET | `/datasets` | List user's datasets |
| DELETE | `/datasets/{id}` | Delete dataset |
| POST | `/train/automl` | Submit AutoML job |
| POST | `/train/specific` | Train specific algorithms |
| GET | `/jobs/{id}` | Get job status |
| GET | `/jobs` | List user's jobs |
| POST | `/jobs/{id}/cancel` | Cancel running job |
| GET | `/models` | List user's models |
| GET | `/models/{id}/leaderboard` | Get model leaderboard |
| POST | `/models/predict` | Make predictions |
| GET | `/health` | Health check |
| GET | `/algorithms` | List available algorithms |

## MCP Tools

| Tool | Description |
|------|-------------|
| `health_check` | Check service status |
| `list_algorithms` | Get available ML algorithms |
| `register_dataset` | Register dataset from MinIO |
| `list_datasets` | List registered datasets |
| `submit_automl_job` | Start AutoML training |
| `submit_specific_job` | Train specific algorithms |
| `get_job_status` | Check training progress |
| `list_jobs` | List all jobs |
| `cancel_job` | Cancel running job |
| `list_models` | List trained models |
| `get_model_leaderboard` | Get model comparison |
| `predict` | Make predictions |

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
