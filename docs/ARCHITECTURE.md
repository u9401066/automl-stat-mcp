# AutoML MCP System - Architecture

> Last Updated: 2025-12-12

## Overview

This system provides AI Agents with AutoML and statistical analysis capabilities through MCP (Model Context Protocol). The architecture follows a microservices pattern with clear separation of concerns.

## System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent Layer                                  │
│  Claude Desktop / VS Code Copilot / Custom AI Applications                  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ MCP Protocol (SSE)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Server (8002)                                  │
│                        automl-mcp-server/                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Tool Handlers                                                       │    │
│  │  ├── automl_tools.py      → AutoML training & prediction            │    │
│  │  ├── statistics_tools.py  → Statistical analysis (LOCAL compute)    │    │
│  │  ├── data_cleaning_tools.py → Data preprocessing                    │    │
│  │  └── result_storage.py    → Result persistence (Redis + MinIO)      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  API Clients                                                         │    │
│  │  ├── automl_client.py → Calls AutoML Service REST API               │    │
│  │  └── stats_client.py  → Calls Stats Service REST API                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ HTTP REST
                    ┌────────────────┴─────────────────┐
                    ▼                                  ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│     AutoML Service (8001)        │  │     Stats Service (8003)         │
│       automl-service/            │  │       stats-service/             │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │
│  │ REST API Endpoints         │  │  │  │ REST API Endpoints         │  │
│  │ ├── /datasets/*           │  │  │  │ ├── /stats/*               │  │
│  │ ├── /jobs/*               │  │  │  │ ├── /cleaning/*            │  │
│  │ └── /models/*             │  │  │  │ └── /storage/*  ← NEW      │  │
│  └────────────────────────────┘  │  │  └────────────────────────────┘  │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │
│  │ DDD Architecture          │  │  │  │ Services                    │  │
│  │ ├── domain/               │  │  │  │ ├── stats_router.py        │  │
│  │ ├── application/          │  │  │  │ ├── cleaning_router.py     │  │
│  │ └── infrastructure/       │  │  │  │ └── storage_router.py      │  │
│  └────────────────────────────┘  │  │  └────────────────────────────┘  │
└──────────────────┬───────────────┘  └──────────────────┬───────────────┘
                   │ Celery Tasks                        │ Celery Tasks
                   ▼                                     ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│     AutoML Worker                │  │     Stats Worker                 │
│       automl-worker/             │  │       stats-worker/              │
│  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │
│  │ ML Training                │  │  │  │ Analysis Tasks             │  │
│  │ └── AutoGluon 1.3.1       │  │  │  │ ├── EDA (ydata-profiling)  │  │
│  │     • Binary              │  │  │  │ ├── TableOne               │  │
│  │     • Multiclass          │  │  │  │ ├── Survival (lifelines)   │  │
│  │     • Regression          │  │  │  │ ├── ROC/AUC                │  │
│  └────────────────────────────┘  │  │  │ └── Power Analysis        │  │
│                                  │  │  └────────────────────────────┘  │
│  Scaling: 4 workers default      │  │  ┌────────────────────────────┐  │
│                                  │  │  │ Visualization              │  │
│                                  │  │  │ └── Publication-quality    │  │
│                                  │  │  │     charts (matplotlib)    │  │
│                                  │  │  └────────────────────────────┘  │
│                                  │  │  Scaling: 2 workers default      │
└──────────────────────────────────┘  └──────────────────────────────────┘
                   │                                     │
                   └──────────────┬──────────────────────┘
                                  ▼
               ┌──────────────────────────────────────┐
               │     Infrastructure Layer             │
               │                                      │
               │  ┌──────────────────────────────┐   │
               │  │  Redis (6379)                │   │
               │  │  • Job Queue (Celery)        │   │
               │  │  • Result Cache (7-day TTL)  │   │
               │  │  • Session Storage           │   │
               │  └──────────────────────────────┘   │
               │                                      │
               │  ┌──────────────────────────────┐   │
               │  │  MinIO (9000)                │   │
               │  │  Buckets:                    │   │
               │  │  • automl-data     → Datasets│   │
               │  │  • automl-models   → Models  │   │
               │  │  • automl-results  → Results │   │
               │  │  • stats-reports   → Reports │   │
               │  └──────────────────────────────┘   │
               │                                      │
               │  ┌──────────────────────────────┐   │
               │  │  Volume Mounts               │   │
               │  │  • /data/sample_data (RO)   │   │
               │  │  • /data/projects (RW)      │   │
               │  └──────────────────────────────┘   │
               └──────────────────────────────────────┘
```

## Data Flow

### 1. ML Training Flow

```
Agent                MCP Server           AutoML Service         AutoML Worker
  │                      │                      │                      │
  ├── upload_dataset ───►│                      │                      │
  │                      ├── POST /datasets ───►│                      │
  │                      │◄── dataset_id ───────┤                      │
  │◄── dataset_id ───────┤                      │                      │
  │                      │                      │                      │
  ├── submit_automl_job ►│                      │                      │
  │                      ├── POST /jobs ────────►│                      │
  │                      │                      ├── Queue Job ─────────►│
  │                      │◄── job_id ───────────┤                      │
  │◄── job_id ───────────┤                      │                      │
  │                      │                      │            Training...│
  │                      │                      │◄── Complete ─────────┤
  ├── get_job_status ───►│                      │                      │
  │                      ├── GET /jobs/{id} ───►│                      │
  │◄── status, model_id ─┤◄─────────────────────┤                      │
```

### 2. Statistics Analysis Flow (Local Compute)

```
Agent                MCP Server           Stats Service          Redis/MinIO
  │                      │                      │                      │
  ├── compare_groups ───►│                      │                      │
  │                      │                      │                      │
  │                      │ [LOCAL COMPUTE]      │                      │
  │                      │ ├── Read CSV         │                      │
  │                      │ ├── pandas/scipy     │                      │
  │                      │ └── Calculate stats  │                      │
  │                      │                      │                      │
  │                      ├── POST /storage ────►│                      │
  │                      │                      ├── Save to Redis ─────►│
  │                      │                      ├── Save to MinIO ─────►│
  │                      │◄── result_id ────────┤◄─────────────────────┤
  │◄── result + id ──────┤                      │                      │
```

### 3. Result Persistence Flow

```
                    ┌─────────────────┐
                    │  Analysis Tool  │
                    │  (MCP Server)   │
                    └────────┬────────┘
                             │ result dict
                             ▼
                    ┌─────────────────┐
                    │ ResultStorage   │
                    │ Client          │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌──────────┐   ┌──────────┐   ┌──────────┐
       │  Redis   │   │  MinIO   │   │ Response │
       │  (temp)  │   │  (perm)  │   │ to Agent │
       │  7-day   │   │ forever  │   │ +result_id
       │  TTL     │   │          │   │ +path    │
       └──────────┘   └──────────┘   └──────────┘

Key Paths:
- Redis: stats:result:{result_id}
- MinIO: automl-results/{user_id}/{analysis_type}/{timestamp}_{result_id}.json
```

## Key Design Decisions

### 1. Local Compute vs Worker Queue

| Type | Approach | Rationale |
|------|----------|-----------|
| Simple Stats | Local (MCP) | Fast response, <1s compute |
| Heavy Analysis | Worker Queue | Async, scalable, minutes |
| ML Training | Worker Queue | GPU support, hours |

### 2. Result Storage Strategy

| Storage | Purpose | TTL | Use Case |
|---------|---------|-----|----------|
| Redis | Fast access | 7 days | Recent results, active sessions |
| MinIO | Permanent | Forever | Audit trail, reproducibility |
| Local `/results/` | User access | - | HTML reports, figures |

### 3. Tool Organization

```
statistics_tools.py
├── Simple stats (pandas/scipy) → Local compute
├── TableOne, EDA → Stats Service API
├── ROC/Survival/Power → Stats Service API
└── All tools → ResultStorage.save_result()
```

## Port Assignments

| Service | Port | Protocol |
|---------|------|----------|
| AutoML API | 8001 | HTTP REST |
| MCP Server | 8002 | SSE (MCP) |
| Stats API | 8003 | HTTP REST |
| Redis | 6379 | Redis Protocol |
| MinIO | 9000 | S3 API |

## Scaling

```yaml
# docker-compose.yml
automl-worker:
  deploy:
    replicas: 4          # Parallel ML training

stats-worker:
  deploy:
    replicas: 2          # Statistical analysis
```

## Security Considerations

1. **User Isolation**: All resources tagged with `user_id`
2. **File Access**: Volume mounts with controlled paths
3. **API Security**: Internal network, nginx reverse proxy for external
4. **No Direct MinIO**: All access through service APIs

## Technology Stack

| Layer | Technology |
|-------|------------|
| AI Agent Protocol | MCP (Model Context Protocol) |
| API Framework | FastAPI + Pydantic |
| ML Framework | AutoGluon 1.3.1 |
| Task Queue | Celery + Redis |
| Statistics | scipy, statsmodels, lifelines, tableone |
| Visualization | matplotlib, seaborn, statannotations |
| Storage | Redis (cache) + MinIO (objects) |
| Containers | Docker Compose |

## Related Documents

- [MCP Tools Inventory](MCP_TOOLS_INVENTORY.md) - Complete tool list
- [Deployment Guide](deployment-guide.md) - Setup instructions
- [ROADMAP](ROADMAP.md) - Development plans
