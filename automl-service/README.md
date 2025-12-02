# AutoML Service

AutoML Service using AutoGluon with DDD architecture.

## Features

- **AutoML**: Automatic model selection and hyperparameter tuning
- **Specific Training**: Train with specific algorithms (XGB, GBM, RF, etc.)
- **Model Comparison**: Compare multiple algorithms with leaderboard
- **Async Training**: Non-blocking training with WebSocket progress updates
- **Multi-user Support**: User/session resource isolation
- **MinIO Integration**: File storage for datasets

## Architecture

```
src/
├── domain/           # Domain Layer (Entities, Value Objects, Events)
│   ├── models/       # Dataset, MLModel, Job, TrainingConfig
│   ├── repositories.py  # Repository interfaces
│   ├── services.py   # Domain service interfaces
│   └── events.py     # Domain events
├── application/      # Application Layer (Use Cases)
│   ├── dto.py        # Data Transfer Objects
│   ├── use_cases.py  # Training use cases
│   └── model_use_cases.py  # Model management use cases
├── infrastructure/   # Infrastructure Layer (Implementations)
│   ├── repositories.py  # In-memory repositories
│   ├── storage.py    # MinIO file storage
│   ├── ml_engine.py  # AutoGluon engine
│   └── job_worker.py # Background job worker
└── interface/        # Interface Layer (API)
    └── api/
        ├── routes/   # FastAPI routers
        ├── schemas.py  # Pydantic schemas
        └── dependencies.py  # DI container
```

## Quick Start

### Using Docker Compose

```bash
docker-compose up -d
```

This starts:
- MinIO on port 9000 (console on 9001)
- AutoML Service on port 8001

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API Endpoints

### Datasets
- `POST /datasets/register` - Register a dataset from MinIO
- `GET /datasets` - List user's datasets
- `DELETE /datasets/{id}` - Delete a dataset

### Training
- `POST /train/automl` - Submit AutoML training job
- `POST /train/specific` - Train with specific algorithms
- `POST /train/compare` - Compare multiple algorithms

### Jobs
- `GET /jobs/{id}` - Get job status
- `GET /jobs` - List user's jobs
- `DELETE /jobs/{id}` - Cancel a job
- `WebSocket /jobs/ws/{id}` - Real-time progress updates

### Models
- `GET /models` - List user's models
- `GET /models/{id}/leaderboard` - Get model leaderboard
- `POST /models/predict` - Make predictions
- `DELETE /models/{id}` - Delete a model

## Available Algorithms

| Code | Algorithm |
|------|-----------|
| GBM | LightGBM |
| CAT | CatBoost |
| XGB | XGBoost |
| RF | Random Forest |
| XT | Extremely Randomized Trees |
| KNN | K-Nearest Neighbors |
| LR | Linear Model |
| NN_TORCH | Neural Network (PyTorch) |
| FASTAI | FastAI Neural Network |

## Example Usage

### 1. Upload dataset to MinIO

Use MinIO console (http://localhost:9001) or mc client.

### 2. Register dataset

```bash
curl -X POST "http://localhost:8001/datasets/register" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user1" \
  -d '{
    "name": "my_dataset",
    "minio_path": "automl-datasets/data.csv"
  }'
```

### 3. Submit training job

```bash
curl -X POST "http://localhost:8001/train/automl" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user1" \
  -d '{
    "dataset_id": "<dataset_id>",
    "target_column": "target",
    "problem_type": "binary",
    "time_limit": 300
  }'
```

### 4. Check job status

```bash
curl "http://localhost:8001/jobs/<job_id>" \
  -H "X-User-Id: user1"
```

### 5. Make predictions

```bash
curl -X POST "http://localhost:8001/models/predict" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: user1" \
  -d '{
    "model_id": "<model_id>",
    "dataset_id": "<prediction_dataset_id>"
  }'
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MINIO_ENDPOINT | localhost:9000 | MinIO endpoint |
| MINIO_ACCESS_KEY | minioadmin | MinIO access key |
| MINIO_SECRET_KEY | minioadmin | MinIO secret key |
| MINIO_SECURE | false | Use HTTPS for MinIO |
| MINIO_BUCKET | automl-datasets | Default bucket |
| API_HOST | 0.0.0.0 | API host |
| API_PORT | 8001 | API port |
| AUTOGLUON_PRESETS | medium_quality | AutoGluon presets |
| DEFAULT_TIME_LIMIT | 300 | Default training time (seconds) |

## License

MIT
