"""
AutoML MCP Server Configuration
"""
import os
from dataclasses import dataclass


@dataclass
class McpServerConfig:
    """Configuration for MCP server"""

    name: str = "AutoML MCP Server"
    version: str = "1.0.0"
    json_response: bool = True

    # AutoML Service endpoint
    automl_service_url: str = os.getenv("AUTOML_SERVICE_URL", "http://localhost:8001")

    # Timeout for HTTP requests (seconds)
    http_timeout: int = int(os.getenv("HTTP_TIMEOUT", "30"))

    instructions: str = """
AutoML MCP Server - 自動機器學習 MCP 伺服器

Provides AutoML capabilities for AI Agents to train and compare ML models.

## 🔍 RECOMMENDED USAGE PATTERN

### Path A: Full AutoML (Automatic Model Selection)
```
1. register_dataset(minio_path)        → Register dataset, get dataset_id
2. submit_automl_job(dataset_id, ...)  → Start training, get job_id
3. get_job_status(job_id)              → Check progress (repeat until complete)
4. get_model_leaderboard(model_id)     → See all trained models ranked
5. predict(model_id, dataset_id)       → Make predictions
```

### Path B: Specific Algorithm Training
```
1. list_algorithms()                   → See available algorithms
2. submit_specific_job(dataset_id, algorithms=["XGB", "RF"])
3. get_job_status(job_id)              → Check progress
4. get_model_leaderboard(model_id)     → Compare results
```

### Path C: Compare Algorithms
```
1. submit_compare_job(dataset_id, algorithms=["XGB", "GBM", "RF", "NN_TORCH"])
2. get_job_status(job_id)              → Wait for completion
3. get_model_leaderboard(model_id)     → See comparison results
```

## ⚠️ IMPORTANT: Long-running Training

AutoML training can take minutes to hours. The MCP tools are designed to:
1. `submit_*_job` returns immediately with a job_id
2. Use `get_job_status` to poll for progress
3. When status is "completed", use the model_id for predictions

This allows you to:
- Inform the user that training has started
- Check progress periodically
- Continue other conversations while waiting
- Report results when complete

## 📊 AVAILABLE ALGORITHMS

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
"""


# Default configuration instance
default_config = McpServerConfig()
