# AutoGluon Worker

Worker service that runs AutoGluon training jobs.

## Key Feature: Zero Maintenance

Uses official AutoGluon Docker image. To update AutoGluon:

```dockerfile
# Just change this line in Dockerfile:
FROM autogluon/autogluon:1.2.0-cpu-py3.10
# To:
FROM autogluon/autogluon:1.3.0-cpu-py3.10
```

Then rebuild:
```bash
docker-compose build automl-worker
docker-compose up -d automl-worker
```

## Architecture

```
Redis Queue                    MinIO
    │                            │
    ▼                            ▼
┌─────────────────────────────────────────┐
│         AutoGluon Worker                │
│  (autogluon/autogluon:x.x.x image)      │
│                                         │
│  1. Pop job from Redis                  │
│  2. Download dataset from MinIO         │
│  3. Run AutoGluon training              │
│  4. Upload model to MinIO               │
│  5. Update status in Redis              │
│                                         │
│  ⚠️ No local storage - all temp files   │
│     cleaned after each job              │
└─────────────────────────────────────────┘
```

## Scaling

Run multiple workers for parallel training:

```bash
docker-compose up -d --scale automl-worker=3
```
