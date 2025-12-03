# AutoML MCP System

Multi-user AutoML system accessible via AI Agents through MCP (Model Context Protocol).

**Features:**
- 🤖 **AutoML Training** - Automatic model selection with AutoGluon
- 📊 **Smart Statistical Analysis** - Intelligent auto-analysis with automatic method selection
- 🔌 **MCP Integration** - Direct access from AI Agents (Claude, Copilot)
- 🔒 **Enterprise Ready** - HTTPS, POST-only API, multi-user isolation

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](docs/deployment-guide.md) | 完整部署教學（開發/生產/企業HTTPS） |
| [README.md](README.md) | 快速入門與架構說明 |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Server (8002)                               │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐   │
│  │      AutoML Tools (23)          │  │      Stats Tools (12)           │   │
│  │  register_dataset, train, ...   │  │  auto_analyze, eda, tableone    │   │
│  └───────────────┬─────────────────┘  └───────────────┬─────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              🎯 Smart Workflow Tools (3)                             │   │
│  │  start_data_analysis, execute_analysis_ticket, check_progress       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└──────────────────┼────────────────────────────────────┼─────────────────────┘
                   │                                    │
                   ▼                                    ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│      AutoML API (8001)       │      │      Stats API (8003)        │
│  • Dataset management        │      │  • Auto analysis engine      │
│  • Training job submission   │      │  • EDA endpoints             │
│  • Model management          │      │  • TableOne endpoints        │
└──────────────┬───────────────┘      └──────────────┬───────────────┘
               │                                     │
               ▼                                     ▼
┌──────────────────────────────┐      ┌──────────────────────────────┐
│     AutoML Worker            │      │     Stats Worker             │
│  • AutoGluon 1.3.1           │      │  • ydata-profiling           │
│  • Model training            │      │  • tableone, scipy, statsmodels│
└──────────────┬───────────────┘      └──────────────┬───────────────┘
               │                                     │
               └──────────────┬──────────────────────┘
                              ▼
               ┌──────────────────────────────┐
               │   Shared Infrastructure      │
               │  ┌────────┐    ┌────────┐   │
               │  │ Redis  │    │ MinIO  │   │
               │  │ (6379) │    │ (9000) │   │
               │  └────────┘    └────────┘   │
               └──────────────────────────────┘
```

## 🧠 Smart Auto-Analysis

The `auto_analyze` tool automatically:

1. **Data Quality Check** - Missing values, outliers, duplicates
2. **Variable Type Inference** - Numeric, categorical, datetime, ID columns
3. **Descriptive Statistics** - Automatically chooses appropriate measures
4. **Hypothesis Testing** - Normality tests to determine parametric vs non-parametric
5. **Association Analysis** - Correlation, chi-square, t-test based on variable types
6. **Recommendations** - Data cleaning, feature engineering, suitable ML models

```
User: "Analyze this dataset"
AI:   auto_analyze(dataset_id) → Complete statistical report with recommendations
```

## Components

| Component | Directory | Purpose | Tech Stack | Status |
|-----------|-----------|---------|------------|--------|
| AutoML API | `automl-service/` | REST API for job/dataset management | FastAPI, Redis, DDD | ✅ Ready |
| AutoML MCP | `automl-mcp-server/` | MCP server for AI agents | FastMCP, httpx | ✅ Ready |
| AutoML Worker | `automl-worker/` | ML training execution | AutoGluon 1.3.1 | ✅ Ready |
| Stats API | `stats-service/` | Statistical analysis API | FastAPI, Redis | ✅ Ready |
| Stats Worker | `stats-worker/` | EDA & TableOne execution | ydata-profiling, tableone | ✅ Ready |

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

### 4. Scale Workers (Optional)

```bash
# Scale AutoML workers to 8 for high concurrency
docker compose up -d --scale automl-worker=8

# Scale Stats workers to 4
docker compose up -d --scale stats-worker=4

# Scale both
docker compose up -d --scale automl-worker=8 --scale stats-worker=4
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

## 🔒 Enterprise HTTPS Deployment

For enterprise environments requiring HTTPS and POST-only API access:

### Security Features

| Feature | Description |
|---------|-------------|
| **HTTPS Only** | TLS 1.2/1.3, HTTP redirects to HTTPS |
| **POST-Only API** | All external endpoints accept POST only |
| **No Internal Exposure** | Redis, API, Workers not exposed externally |
| **Rate Limiting** | 10 req/s per IP with burst handling |
| **Security Headers** | HSTS, X-Frame-Options, CSP, etc. |

### Setup

1. **Prepare SSL Certificates**

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Option A: Use your organization's certificates
cp /path/to/your/server.crt nginx/ssl/
cp /path/to/your/server.key nginx/ssl/

# Option B: Generate self-signed (for testing only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/server.key \
  -out nginx/ssl/server.crt \
  -subj "/CN=automl.local"
```

2. **Configure Environment**

```bash
cp .env.example .env
nano .env
```

```bash
# Required
MINIO_ENDPOINT=your-minio-host:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=true  # Use HTTPS for MinIO too

# Optional HTTPS settings
HTTPS_PORT=443
HTTP_PORT=80
```

3. **Start HTTPS Stack**

```bash
docker-compose -f docker-compose.https.yml up -d
```

### POST-Only API Endpoints

External clients must use these POST endpoints:

| Endpoint | Description | Request Body |
|----------|-------------|--------------|
| `POST /api/v1/datasets/list` | List datasets | `{}` |
| `POST /api/v1/datasets/get` | Get dataset | `{"dataset_id": "..."}` |
| `POST /api/v1/jobs/list` | List jobs | `{}` |
| `POST /api/v1/jobs/get` | Get job status | `{"job_id": "..."}` |
| `POST /api/v1/models/list` | List models | `{}` |
| `POST /api/v1/models/get` | Get model | `{"model_id": "..."}` |
| `POST /api/v1/models/leaderboard` | Get leaderboard | `{"model_id": "..."}` |

All existing POST endpoints (training, predict, etc.) work as-is.

### Example: HTTPS POST Request

```bash
curl -X POST https://your-server/api/v1/jobs/get \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user123" \
  -d '{"job_id": "job-abc-123"}'
```

### MCP Transport Modes

| Mode | Use Case | Protocol |
|------|----------|----------|
| `stdio` | Local (Claude Desktop, VS Code) | stdin/stdout |
| `sse` | Development/Internal | GET + Server-Sent Events |
| `http` | **Enterprise (POST-only)** | POST + Streamable HTTP |

For enterprise HTTPS deployment, MCP uses `streamable-http` transport which is fully POST-based.

```yaml
# In docker-compose.https.yml
environment:
  - MCP_MODE=http  # Uses POST-only streamable-http transport
```

## Usage Flow

### 🎯 Quick Path (Recommended for Agents)

```
User: "Train a model on my-bucket/data.csv to predict 'outcome'"

Agent:
1. quick_train(minio_path="my-bucket/data.csv", target="outcome", problem_type="binary")
   → Waits for training, returns model_id + leaderboard

2. "Training complete! Best model: XGBoost with 95% accuracy"

3. predict(model_id, new_dataset_id)
   → Predictions
```

### 📊 Detailed Path (Full Control)

```
User: "Train a model on my dataset to predict 'outcome'"

Agent:
1. register_dataset(minio_path="bucket/data.csv")
   → dataset_id

2. analyze_dataset(dataset_id, target="outcome")
   → Recommendations: presets="high_quality", time_limit=600

3. submit_automl_job(dataset_id, target="outcome", problem_type="binary")
   → job_id (returns immediately!)

4. "Training started. I'll check progress..."

5. wait_for_job(job_id, timeout=3600)  # or poll with get_job_status
   → status: "completed", model_id

6. get_model_leaderboard(model_id)
   → Show results to user

7. predict(model_id, new_dataset_id)
   → Predictions
```

### 📋 Resource Management

```
Agent: get_training_summary(user_id)
→ Overview of all datasets, jobs, models
```

## Update AutoGluon

Just change the tag in `automl-worker/Dockerfile`:

```dockerfile
# Available tags: https://hub.docker.com/r/autogluon/autogluon/tags
FROM autogluon/autogluon:1.3.1-cpu-framework-ubuntu22.04-py3.11  # Current
```

Then rebuild:
```bash
docker build -t automl-worker ./automl-worker
docker rm -f automl-worker
docker run -d --name automl-worker ... automl-worker  # Same run command as above
```

## GPU Support

The worker automatically detects GPU availability and uses it for neural network training.

### Option 1: Single GPU Worker

```bash
# Build GPU image
docker build -f automl-worker/Dockerfile.gpu -t automl-worker-gpu ./automl-worker

# Run with NVIDIA runtime
docker run -d --name automl-worker-gpu \
  --network automl-network \
  --runtime nvidia \
  --gpus all \
  -e REDIS_HOST=automl-redis \
  -e MINIO_ENDPOINT=$MINIO_ENDPOINT \
  -e MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY \
  -e MINIO_SECRET_KEY=$MINIO_SECRET_KEY \
  automl-worker-gpu
```

### Option 2: Docker Compose with GPU

```bash
# Start all services with GPU worker
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### GPU Auto-Detection

The worker automatically:
1. Detects if CUDA is available
2. Uses GPU for neural network models (NeuralNetTorch, NeuralNetFastAI)
3. Falls back to CPU if GPU unavailable

Worker logs show:
```
Device: GPU: NVIDIA GeForce RTX 3080 (x1)
Training with GPU acceleration
```

or:
```
Device: CPU only (CUDA not available)
Training with CPU
```

## Scaling Workers

Workers are scaled via docker compose. Default is 4 workers.

### Horizontal Scaling

```bash
# Scale to 8 workers for high concurrency
docker compose up -d --scale automl-worker=8

# Scale down to 2 workers
docker compose up -d --scale automl-worker=2
```

### Mixed GPU/CPU Scaling

Run both GPU and CPU workers for optimal resource usage:

```bash
# GPU workers with compose override
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Worker Monitoring

Workers register themselves in Redis for monitoring:

```bash
# Check active workers
redis-cli SMEMBERS automl:workers:active

# Get worker info
redis-cli HGETALL automl:workers:worker-1
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

### Basic Tools (API Proxy)

| Tool | Description |
|------|-------------|
| `health_check` | Check service status |
| `list_algorithms` | Get available ML algorithms |
| `register_dataset` | Register dataset from MinIO |
| `list_datasets` | List registered datasets |
| `delete_dataset` | Delete a dataset |
| `submit_automl_job` | Start AutoML training (async) |
| `submit_specific_job` | Train specific algorithms (async) |
| `submit_compare_job` | Compare multiple algorithms (async) |
| `get_job_status` | Check training progress |
| `list_jobs` | List all jobs |
| `cancel_job` | Cancel running job |
| `list_models` | List trained models |
| `get_model_leaderboard` | Get model comparison |
| `predict` | Make predictions |
| `delete_model` | Delete a model |

### 🚀 Smart Orchestration Tools

These tools combine multiple operations for better Agent UX:

| Tool | Description | Use Case |
|------|-------------|----------|
| `quick_train` | 🎯 **Fastest path**: register + train + wait | "Train a model on this CSV" |
| `train_and_wait` | Submit training and block until complete | Full control with waiting |
| `wait_for_job` | Wait for any job to complete with timeout | Long-running jobs |
| `analyze_dataset` | Get training recommendations | Optimize settings before training |
| `get_training_summary` | Overview of all ML resources | Dashboard view |

### Example: One-Call Training

```python
# Agent uses quick_train - one call does everything!
result = quick_train(
    minio_path="my-bucket/sales_data.csv",
    target_column="revenue",
    problem_type="regression",
    user_id="user123",
    time_limit=300
)

# Returns:
# {
#   "dataset_id": "abc-123",
#   "job_id": "def-456", 
#   "model_id": "ghi-789",
#   "status": "completed",
#   "summary": "✅ Model ready! 14 models trained in 2.5 min",
#   "leaderboard": [...]
# }
```

### Example: Step-by-Step with Analysis

```python
# 1. Analyze dataset first
analysis = analyze_dataset(dataset_id, target_column, user_id)
# Returns recommendations for presets, time_limit, warnings

# 2. Train with recommended settings
result = train_and_wait(
    dataset_id=dataset_id,
    target_column=target_column,
    problem_type=analysis["recommended_problem_type"],
    presets=analysis["recommendations"]["presets"],
    time_limit=analysis["recommendations"]["time_limit"],
    user_id=user_id
)

# 3. Make predictions
predictions = predict(model_id=result["model_id"], dataset_id=test_data_id, user_id=user_id)
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
├── automl-service/          # REST API Service (DDD Architecture)
│   ├── src/
│   │   ├── domain/          # Domain Layer (models, repositories interfaces)
│   │   ├── application/     # Application Layer (use cases, DTOs)
│   │   ├── infrastructure/  # Infrastructure (Redis, MinIO, repo implementations)
│   │   └── interface/       # Interface Layer (FastAPI Routes)
│   ├── Dockerfile
│   └── requirements.txt
│
├── automl-mcp-server/       # MCP Server (32 tools total)
│   ├── src/
│   │   └── infrastructure/mcp/
│   │       ├── handlers/
│   │       │   ├── automl_tools.py      # 20 AutoML tools
│   │       │   └── statistics_tools.py  # 12 Statistics tools
│   │       ├── client.py    # HTTP Client
│   │       └── server.py    # FastMCP Server
│   ├── Dockerfile
│   └── requirements.txt
│
├── automl-worker/           # AutoGluon Worker
│   ├── src/worker.py        # Job Consumer
│   └── Dockerfile           # Uses official AutoGluon image
│
├── stats-service/           # Statistics API Service (DDD Architecture)
│   ├── src/
│   │   ├── domain/          # Domain Layer (models, repositories interface)
│   │   ├── application/     # Application Layer (use cases, DTOs)
│   │   ├── infrastructure/  # Infrastructure (Redis repos, MinIO, job queue)
│   │   └── routes/          # Interface Layer (FastAPI routes)
│   ├── Dockerfile
│   └── requirements.txt
│
├── stats-worker/            # Statistics Worker
│   ├── src/
│   │   └── tasks/
│   │       ├── eda_task.py           # ydata-profiling EDA
│   │       ├── tableone_task.py      # TableOne summary stats
│   │       └── auto_analyze_task.py  # Intelligent auto analysis (~830 lines)
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml       # Full stack deployment
├── docker-compose.gpu.yml   # GPU overlay
├── .env.example             # Environment template
└── .vscode/mcp.json         # VS Code MCP config
```

## Architecture

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MCP Protocol                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        automl-mcp-server                             │   │
│  │  ┌─────────────────┐    ┌─────────────────────────────────────────┐ │   │
│  │  │ AutoML Tools(20)│    │ Statistics Tools (12)                   │ │   │
│  │  │ - register      │    │ - submit_eda_job, submit_tableone_job   │ │   │
│  │  │ - train         │    │ - auto_analyze, run_quick_auto_analyze  │ │   │
│  │  │ - predict       │    │ - analyze_csv_directly, get_quick_stats │ │   │
│  │  └────────┬────────┘    └────────────────┬────────────────────────┘ │   │
│  └───────────┼──────────────────────────────┼──────────────────────────┘   │
│              │ HTTP                         │ HTTP                         │
│  ┌───────────▼───────────┐      ┌───────────▼───────────┐                 │
│  │    automl-service     │      │    stats-service      │                 │
│  │  ┌─────────────────┐  │      │  ┌─────────────────┐  │                 │
│  │  │ Dataset Mgmt    │  │      │  │ EDA/TableOne    │  │                 │
│  │  │ Job Submission  │  │      │  │ Auto Analyze    │  │                 │
│  │  │ Model Mgmt      │  │      │  │ Direct Analyze  │  │                 │
│  │  └────────┬────────┘  │      │  └────────┬────────┘  │                 │
│  └───────────┼───────────┘      └───────────┼───────────┘                 │
│              │ Redis Queue                  │ Redis Queue                  │
│  ┌───────────▼───────────┐      ┌───────────▼───────────┐                 │
│  │    automl-worker      │      │    stats-worker       │                 │
│  │  ┌─────────────────┐  │      │  ┌─────────────────┐  │                 │
│  │  │ AutoGluon       │  │      │  │ ydata-profiling │  │                 │
│  │  │ Training Engine │  │      │  │ tableone        │  │                 │
│  │  └─────────────────┘  │      │  │ statsmodels     │  │                 │
│  └───────────────────────┘      │  └─────────────────┘  │                 │
│                                 └───────────────────────┘                 │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        Shared Infrastructure                         │ │
│  │  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐        │ │
│  │  │     Redis     │    │     MinIO     │    │   PostgreSQL  │        │ │
│  │  │ - Job Queues  │    │ - CSV Files   │    │ - (optional)  │        │ │
│  │  │ - Dataset Meta│    │ - Models      │    │               │        │ │
│  │  │ - Results     │    │ - Reports     │    │               │        │ │
│  │  └───────────────┘    └───────────────┘    └───────────────┘        │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Use Case Flows

**Use Case 1: AutoML Training (Register → Train → Predict)**
```
User → MCP → automl-service → Redis Queue → automl-worker → MinIO (model)
                    ↓
            Redis (datasets:{id})  ← Shared metadata for both services
```

**Use Case 2: Model Prediction**
```
User → MCP → automl-service → Load model from MinIO → Return predictions
```

**Use Case 3: Statistical Analysis (EDA, TableOne, Auto Analyze)**
```
User → MCP → stats-service → Redis (read datasets:{id}) → Redis Queue → stats-worker
                                                                              ↓
                                                                    MinIO (CSV read)
                                                                              ↓
                                                                    MinIO (report save)
```

**Use Case 4: Direct Analysis (No MinIO Storage)**
```
User → MCP → stats-service → Redis Queue → stats-worker → Return results
         (CSV content in request)     (process in memory)
```

### ⚠️ Architecture Decisions

#### Decision 1: Stats Service Dataset Dependency ✅ ACCEPTED

**Design Choice**: Stats service uses shared dataset metadata from Redis, which is written by automl-service during `register_dataset`.

**Rationale**:
1. **Single Source of Truth** - Dataset metadata managed in one place
2. **Direct Analysis Available** - `/direct/analyze` endpoints don't require registration
3. **Avoids Duplication** - No need for separate dataset registration logic

**Usage Patterns**:

| Pattern | Use Case | API |
|---------|----------|-----|
| **Quick Analysis** | One-time analysis, temporary data | `/direct/analyze`, `/direct/quick-stats` |
| **Tracked Analysis** | Registered datasets, ML pipeline | `/auto-analyze/submit` with `dataset_id` |

**Flow for Quick Analysis (No Registration)**:
```
User → analyze_csv_directly(csv_content) → stats-service → Results
```

**Flow for Tracked Analysis (With Registration)**:
```
1. User → register_dataset(minio_path) → automl-service → dataset_id
2. User → auto_analyze(dataset_id) → stats-service → Results (linked to dataset)
```

**Recommendation**: Use `analyze_csv_directly` or `get_quick_stats` for ad-hoc analysis. Use `auto_analyze` with `dataset_id` when the dataset is part of an ML pipeline.

#### Issue 2: ~~AutoML Service Lacks Direct Analyze~~ ✅ RESOLVED

**Solution Implemented**: Added direct analyze endpoints to automl-service:
- `POST /direct/analyze` - ML training preparation analysis
- `POST /direct/quick-stats` - Quick statistics
- `POST /direct/preview` - Preview data before registration

**MCP Tools Added**:
- `direct_ml_analyze` - Analyze CSV for ML recommendations
- `direct_ml_quick_stats` - Quick statistics
- `direct_preview_data` - Preview before MinIO upload

#### Issue 3: ~~Stats Service Lacks DDD Architecture~~ ✅ RESOLVED

**Solution Implemented**: Refactored stats-service to follow DDD architecture:

**New Structure**:
```
stats-service/src/
├── domain/              ✅ NEW
│   ├── models/
│   │   └── stats_job.py    # StatsJob aggregate, StatsJobId value object
│   └── repositories.py     # StatsJobRepository interface
├── application/         ✅ NEW
│   ├── dto.py              # Request/Response DTOs
│   └── use_cases.py        # SubmitAutoAnalyze, SubmitEDA, SubmitTableOne, etc.
├── infrastructure/      ✅ UPDATED
│   └── repositories.py     # RedisStatsJobRepository, RedisJobQueue
└── routes/              ✅ REFACTORED (acts as Interface layer)
    ├── auto_analyze.py     # Uses SubmitAutoAnalyzeUseCase
    ├── eda.py              # Uses SubmitEDAUseCase
    ├── tableone.py         # Uses SubmitTableOneUseCase
    ├── jobs.py             # Uses GetJobStatus/Result/ListUseCase
    └── direct.py           # Uses domain models directly
```

## MCP Tool Summary

| Category | Count | Tools |
|----------|-------|-------|
| AutoML Training | 8 | register_dataset, submit_automl_job, submit_specific_job, submit_compare_job, get_job_status, list_jobs, cancel_job, wait_for_job |
| AutoML Models | 4 | list_models, get_model_leaderboard, predict, delete_model |
| AutoML Datasets | 3 | list_datasets, delete_dataset, analyze_dataset |
| AutoML Smart | 3 | quick_train, train_and_wait, get_training_summary |
| AutoML Direct | 3 | direct_ml_analyze, direct_ml_quick_stats, direct_preview_data |
| AutoML Utility | 2 | health_check, list_algorithms |
| **AutoML Total** | **23** | |
| Statistics EDA | 3 | submit_eda_job, run_quick_eda, preview_dataset_stats |
| Statistics TableOne | 3 | submit_tableone_job, run_quick_tableone, get_column_suggestions |
| Statistics Auto | 3 | auto_analyze, run_quick_auto_analyze, get_analysis_capabilities |
| Statistics Direct | 2 | analyze_csv_directly, get_quick_stats |
| Statistics Jobs | 1 | get_stats_job_status, get_stats_job_result, list_stats_jobs |
| **Statistics Total** | **12** | |
| 🎯 Smart Workflow | 3 | start_data_analysis, execute_analysis_ticket, check_analysis_progress |
| **Grand Total** | **38** | |

### 🎯 Smart Workflow Tools

The smart workflow tools provide a guided analysis experience:

```
User: "Analyze this data"
     ↓
Agent: start_data_analysis(csv_content) 
     ↓
Returns: Analysis Ticket with data preview and options
     ↓
Agent asks: "Do you want to save this for future use?"
     ↓
User: "Yes, name it sales_data" | "No, just analyze it"
     ↓
Agent: execute_analysis_ticket(ticket_id, save_to_storage=True/False)
     ↓
Returns: Job Ticket with results or tracking info
```

## License

MIT
