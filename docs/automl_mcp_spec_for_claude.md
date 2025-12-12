# AutoML + MCP Server Technical Specification
_For implementation by a Claude Opus 4.5 coding agent_

## 1. Goal and Scope

This document specifies an **AutoML microservice** and an **MCP (Model Context Protocol) server** that exposes this AutoML service as tools callable by agents.

The design assumes:

- Runtime: Python (3.10+)
- Deployment: single-node VM (CPU only is acceptable; GPU is optional)
- Data type: mainly **tabular data** (clinical / research datasets)
- AutoML backend: one of
  - **FLAML** (recommended for lightweight internal deployment), or
  - **auto-sklearn** (alternative; interchangeable at the engine layer)

The target usage pattern:

1. An upstream agent prepares/chooses a dataset (e.g., after data cleaning / feature selection).
2. The agent calls MCP tools to:
   - upload / reference the dataset,
   - start an AutoML training experiment,
   - obtain the best model and metrics,
   - run predictions on new data.
3. The agent uses the results in higher-level workflows (e.g., scenario optimization, risk prediction).

This document focuses on **mechanical / implementation details** so that another agent can implement the code with minimal ambiguity.


## 2. High-Level Architecture

There are three layers:

1. **AutoML Server (FastAPI)**
   - Stateless HTTP API for:
     - dataset registration and storage
     - AutoML training
     - inference with a stored model
   - Uses a local file-based store for simplicity (can later be swapped to DB / object storage).

2. **Core Library**
   - `dataset_store`: managing dataset files and IDs
   - `automl_engine`: running AutoML search with FLAML or auto-sklearn
   - `model_registry`: persisting trained models and metadata
   - `schemas`: Pydantic models for request/response validation

3. **MCP Server**
   - Wraps the AutoML HTTP API as MCP tools.
   - Responsible for:
     - describing tools (metadata + JSON schemas)
     - validating call inputs against schemas
     - forwarding calls to the AutoML server via HTTP
     - returning normalized results to the calling agent


## 3. Project Layout

Create a repository with the following structure:

```text
automl-mcp/
  automl_server/
    app/
      __init__.py
      main.py              # FastAPI entry
      config.py            # configuration constants (paths, port, etc.)
      schemas.py           # Pydantic request/response models
      core/
        __init__.py
        dataset_store.py   # dataset saving/loading
        automl_engine.py   # AutoML logic (FLAML or auto-sklearn)
        model_registry.py  # model save/load, meta info
        metrics.py         # metrics + CV helper
        utils.py           # shared utilities (logging, seeding, etc.)
    models/                # serialized models (.joblib, etc.)
    data/                  # uploaded datasets (.csv, .parquet)
    experiments/           # experiment metadata JSON
    requirements.txt
    README.md

  mcp_server/
    src/
      __init__.py
      server.py            # MCP server entry
      tools.py             # tool definitions, HTTP client wrappers
      config.py            # base URL of AutoML server, timeouts, etc.
    pyproject.toml or requirements.txt

  docs/
    automl_mcp_spec.md     # (this document)
```

The Claude agent should implement the Python code inside `automl_server/` and `mcp_server/` according to the following specifications.


## 4. AutoML Server – Detailed Design

### 4.1 Dependencies

In `automl_server/requirements.txt` include (minimum set):

```text
fastapi
uvicorn
pydantic>=2
pandas
numpy
joblib
flaml             # preferred; OR auto-sklearn (not both required)
scikit-learn
optuna            # optional: only if you use the Optuna-based engine
```

### 4.2 Pydantic Schemas (`app/schemas.py`)

Define the following models (Pydantic v2 style is preferred; v1-compatible is acceptable if needed).

```python
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class DatasetRef(BaseModel):
    dataset_id: str = Field(..., description="Internal dataset identifier")


class UploadDatasetRequest(BaseModel):
    name: str
    description: Optional[str] = None
    # The raw CSV string (including header row)
    csv_content: str


class UploadDatasetResponse(BaseModel):
    dataset_id: str


class AutoMLConfig(BaseModel):
    target_column: str
    problem_type: Literal["binary", "multiclass", "regression"]
    metric: Literal["roc_auc", "accuracy", "neg_log_loss", "rmse"] = "roc_auc"
    max_trials: int = 20
    cv_folds: int = 5
    random_state: int = 42
    # Optional future extension fields:
    # search_time_budget: Optional[int] = None  # seconds
    # allowed_models: Optional[List[str]] = None


class AutoMLTrainRequest(BaseModel):
    dataset: DatasetRef
    config: AutoMLConfig


class AutoMLTrainResult(BaseModel):
    experiment_id: str
    best_model_id: str
    best_score: float
    metric: str
    model_summary: Dict[str, str]


class AutoMLPredictRequest(BaseModel):
    model_id: str
    dataset: DatasetRef


class AutoMLPredictResult(BaseModel):
    model_id: str
    predictions: List[float]
```


### 4.3 Dataset Store (`app/core/dataset_store.py`)

Purpose: store uploaded datasets on disk, and provide an ID-based loading mechanism.

**Requirements:**

- Use a `UUID` string as `dataset_id`.
- Save datasets as CSV files under `automl_server/data/`.
- Maintain an in-memory index: `dataset_id -> file_path`. On process restart, index can be reconstructed by scanning the directory *if needed*. For an initial implementation, you may rebuild lazily when missing.

**Example implementation skeleton:**

```python
import uuid
from pathlib import Path
from typing import Dict
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_DATASET_INDEX: Dict[str, str] = {}


def save_csv_dataset(name: str, csv_content: str) -> str:
    dataset_id = str(uuid.uuid4())
    file_path = DATA_DIR / f"{dataset_id}.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    _DATASET_INDEX[dataset_id] = str(file_path)
    return dataset_id


def load_dataset(dataset_id: str) -> pd.DataFrame:
    if dataset_id not in _DATASET_INDEX:
        file_path = DATA_DIR / f"{dataset_id}.csv"
        if not file_path.exists():
            raise ValueError(f"Unknown dataset_id: {dataset_id}")
        _DATASET_INDEX[dataset_id] = str(file_path)
    file_path = Path(_DATASET_INDEX[dataset_id])
    return pd.read_csv(file_path)
```


### 4.4 Model Registry (`app/core/model_registry.py`)

Purpose: persist trained models and basic metadata.

**Requirements:**

- Use `UUID` as `model_id`.
- Save models as `.joblib` files under `automl_server/models/`.
- Save metadata JSON in `automl_server/experiments/` with filename `{model_id}.meta.json`.

**Example skeleton:**

```python
import uuid
from pathlib import Path
from typing import Dict, Any
import joblib
import json
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

_MODEL_INDEX: Dict[str, str] = {}


def save_model(model: Any, meta: Dict[str, Any]) -> str:
    model_id = str(uuid.uuid4())
    model_path = MODELS_DIR / f"{model_id}.joblib"
    joblib.dump(model, model_path)
    _MODEL_INDEX[model_id] = str(model_path)

    meta_path = EXPERIMENTS_DIR / f"{model_id}.meta.json"
    meta["model_id"] = model_id
    meta["saved_at"] = datetime.utcnow().isoformat()
    meta_path.write_text(json.dumps(meta, indent=2))

    return model_id


def load_model(model_id: str) -> Any:
    if model_id not in _MODEL_INDEX:
        model_path = MODELS_DIR / f"{model_id}.joblib"
        if not model_path.exists():
            raise ValueError(f"Unknown model_id: {model_id}")
        _MODEL_INDEX[model_id] = str(model_path)
    return joblib.load(_MODEL_INDEX[model_id])
```


### 4.5 AutoML Engine (`app/core/automl_engine.py`)

#### Option A: FLAML-based engine (preferred)

FLAML exposes a simple `AutoML` class. The engine should:

- Accept `X`, `y`, `problem_type`, `metric`, `max_trials` (or time budget).
- Configure an `AutoML` instance.
- Fit the AutoML model.
- Return the fitted estimator + best score + metadata.

**Pseudo-code skeleton:**

```python
from typing import Tuple, Dict, Any
import numpy as np
from flaml import AutoML


def run_automl_flaml(
    X,
    y,
    problem_type: str,
    metric: str,
    max_trials: int,
    cv_folds: int,
    random_state: int = 42,
) -> Tuple[object, float, Dict[str, Any]]:
    automl = AutoML()
    settings = {
        "task": "classification" if problem_type in ("binary", "multiclass") else "regression",
        "metric": metric,
        "log_file_name": "flaml.log",
        "time_budget": None,  # can be set from config
        "seed": random_state,
        "eval_method": "cv",
        "n_splits": cv_folds,
        "estimator_list": None,  # or specify ["lgbm", "xgboost", ...]
    }
    automl.fit(X_train=X, y_train=y, **settings)
    best_model = automl.model.estimator
    # Adjust best_score extraction based on FLAML's metric conventions.
    # For simplicity, treat lower loss as better and invert if needed.
    best_score = float(automl.best_loss) * -1.0
    meta = {
        "backend": "flaml",
        "best_config": automl.best_config,
        "metric": metric,
    }
    return best_model, best_score, meta
```

#### Option B: auto-sklearn-based engine

Alternatively, implement a similar function `run_automl_autosklearn(...)` using `AutoSklearnClassifier` or `AutoSklearnRegressor`. Both can coexist; you may add a configuration flag to choose which backend to use.


### 4.6 FastAPI Entry (`app/main.py`)

Implement a FastAPI application exposing at least these endpoints:

1. `POST /datasets/upload`
   - Input: `UploadDatasetRequest`
   - Output: `UploadDatasetResponse`

2. `POST /automl/train`
   - Input: `AutoMLTrainRequest`
   - Behavior:
     - Load dataset by `dataset_id`.
     - Split `X` and `y` using `config.target_column`.
     - Call `run_automl_*` engine.
     - Save the trained model via `model_registry.save_model`.
     - Return `AutoMLTrainResult`.

3. `POST /automl/predict`
   - Input: `AutoMLPredictRequest`
   - Behavior:
     - Load dataset by `dataset_id`.
     - Load model by `model_id`.
     - Run `predict_proba` (preferred) or `predict`.
     - Return `AutoMLPredictResult` with a list of floats.

**Skeleton:**

```python
from fastapi import FastAPI, HTTPException
from .schemas import (
    UploadDatasetRequest,
    UploadDatasetResponse,
    AutoMLTrainRequest,
    AutoMLTrainResult,
    AutoMLPredictRequest,
    AutoMLPredictResult,
)
from .core.dataset_store import save_csv_dataset, load_dataset
from .core.automl_engine import run_automl_flaml
from .core.model_registry import save_model, load_model

app = FastAPI(title="AutoML Server", version="0.1.0")


@app.post("/datasets/upload", response_model=UploadDatasetResponse)
def upload_dataset(req: UploadDatasetRequest):
    dataset_id = save_csv_dataset(req.name, req.csv_content)
    return UploadDatasetResponse(dataset_id=dataset_id)


@app.post("/automl/train", response_model=AutoMLTrainResult)
def automl_train(req: AutoMLTrainRequest):
    try:
        df = load_dataset(req.dataset.dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    cfg = req.config
    if cfg.target_column not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"target_column {cfg.target_column} not found in dataset",
        )

    y = df[cfg.target_column].values
    X = df.drop(columns=[cfg.target_column]).values

    model, best_score, meta = run_automl_flaml(
        X=X,
        y=y,
        problem_type=cfg.problem_type,
        metric=cfg.metric,
        max_trials=cfg.max_trials,
        cv_folds=cfg.cv_folds,
        random_state=cfg.random_state,
    )

    model_meta = {
        "problem_type": cfg.problem_type,
        "metric": cfg.metric,
        "best_score": best_score,
        "target_column": cfg.target_column,
        **meta,
    }
    model_id = save_model(model, model_meta)
    experiment_id = model_id  # for now, treat as same

    return AutoMLTrainResult(
        experiment_id=experiment_id,
        best_model_id=model_id,
        best_score=best_score,
        metric=cfg.metric,
        model_summary=model_meta,
    )


@app.post("/automl/predict", response_model=AutoMLPredictResult)
def automl_predict(req: AutoMLPredictRequest):
    try:
        df = load_dataset(req.dataset.dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        model = load_model(req.model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    X = df.values

    if hasattr(model, "predict_proba"):
        probs = model.predict_proba(X)
        if probs.ndim == 2 and probs.shape[1] == 2:
            preds = probs[:, 1].tolist()
        else:
            preds = probs.tolist()
    else:
        preds = model.predict(X).tolist()

    return AutoMLPredictResult(
        model_id=req.model_id,
        predictions=preds,
    )
```

Run locally with:

```bash
uvicorn app.main:app --reload --port 8001
```


## 5. MCP Server – Design

The MCP server acts as a thin wrapper over the AutoML HTTP API.

### 5.1 Responsibilities

- Define MCP tools for:
  - `upload_dataset`
  - `automl_train`
  - `automl_predict`
- Validate input / output JSON against schemas equivalent to the FastAPI models.
- Forward the tools’ payloads via HTTP POST to the AutoML server.
- Return structured JSON responses to the calling agent.

### 5.2 Configuration (`mcp_server/config.py`)

Define at minimum:

```python
AUTOML_BASE_URL = "http://localhost:8001"
HTTP_TIMEOUT_SECONDS = 60
```


### 5.3 HTTP client (`mcp_server/tools.py`)

Use `httpx` or `requests` inside the MCP server to call the AutoML server.

Example skeleton:

```python
import httpx
from .config import AUTOML_BASE_URL, HTTP_TIMEOUT_SECONDS


async def upload_dataset_tool(name: str, csv_content: str, description: str | None = None) -> dict:
    payload = {
        "name": name,
        "description": description,
        "csv_content": csv_content,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{AUTOML_BASE_URL}/datasets/upload", json=payload)
    resp.raise_for_status()
    return resp.json()


async def automl_train_tool(dataset_id: str, config: dict) -> dict:
    payload = {
        "dataset": {"dataset_id": dataset_id},
        "config": config,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{AUTOML_BASE_URL}/automl/train", json=payload)
    resp.raise_for_status()
    return resp.json()


async def automl_predict_tool(model_id: str, dataset_id: str) -> dict:
    payload = {
        "model_id": model_id,
        "dataset": {"dataset_id": dataset_id},
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{AUTOML_BASE_URL}/automl/predict", json=payload)
    resp.raise_for_status()
    return resp.json()
```


### 5.4 MCP Tool Definitions

Depending on the MCP implementation (Python/Node), define tools roughly with the following **signatures** and **JSON schemas** (conceptual level).

#### Tool: `upload_dataset`

- **Description**: Upload a CSV dataset string and register it for later use in AutoML.
- **Input JSON**:

```json
{
  "name": "string",
  "description": "string (optional)",
  "csv_content": "string (CSV text, including header)"
}
```

- **Output JSON**:

```json
{
  "dataset_id": "string"
}
```


#### Tool: `automl_train`

- **Description**: Train an AutoML model on a registered dataset.
- **Input JSON**:

```json
{
  "dataset_id": "string",
  "config": {
    "target_column": "string",
    "problem_type": "binary | multiclass | regression",
    "metric": "roc_auc | accuracy | neg_log_loss | rmse",
    "max_trials": 20,
    "cv_folds": 5,
    "random_state": 42
  }
}
```

- **Output JSON**:

```json
{
  "experiment_id": "string",
  "best_model_id": "string",
  "best_score": 0.85,
  "metric": "roc_auc",
  "model_summary": {
    "...": "..."
  }
}
```


#### Tool: `automl_predict`

- **Description**: Run inference using a previously trained model on a registered dataset.
- **Input JSON**:

```json
{
  "model_id": "string",
  "dataset_id": "string"
}
```

- **Output JSON**:

```json
{
  "model_id": "string",
  "predictions": [0.12, 0.87, 0.55, "..."]
}
```


## 6. Example Agent Workflow Using MCP Tools

An upstream agent (e.g., a clinical research workflow agent) could perform:

1. **Upload dataset**

   ```json
   {
     "tool": "upload_dataset",
     "arguments": {
       "name": "aki_cohort_2021_2024",
       "description": "Pre-processed AKI cohort with features and AKI label",
       "csv_content": "<CSV string here>"
     }
   }
   ```

   → Receives `dataset_id`.

2. **Train AutoML model**

   ```json
   {
     "tool": "automl_train",
     "arguments": {
       "dataset_id": "the_dataset_id_from_step1",
       "config": {
         "target_column": "AKI_label",
         "problem_type": "binary",
         "metric": "roc_auc",
         "max_trials": 20,
         "cv_folds": 5,
         "random_state": 42
       }
     }
   }
   ```

   → Receives `best_model_id`, `best_score`, `model_summary`.


3. **Predict on new cases**

   - Upload another dataset with the same feature columns but without the target.
   - Call `automl_predict` with `model_id` and `dataset_id` of the new dataset.
   - Use the returned `predictions` in downstream decision logic.


## 7. Non-Functional Requirements and Notes

1. **Reproducibility**
   - Always log:
     - random seed
     - AutoML backend type (flaml / auto-sklearn)
     - configuration used for each experiment.

2. **Safety**
   - The AutoML server must **not** perform arbitrary code execution. It only runs pre-defined AutoML routines.
   - Input size limits should be considered for extremely large CSVs.

3. **Extensibility**
   - The AutoML engine is abstracted in `automl_engine.py`. It should be straightforward to:
     - swap FLAML to auto-sklearn,
     - or add a custom in-house AutoML procedure.

4. **Error Handling**
   - AutoML server returns HTTP 4xx / 5xx with informative messages.
   - MCP layer should translate HTTP errors into tool-level errors that the agent can interpret.


---

This specification is complete enough for a Claude Opus 4.5 coding agent to implement:

- a working AutoML server (FastAPI + AutoML backend),
- a functional MCP server exposing three tools: `upload_dataset`, `automl_train`, `automl_predict`,
- and to integrate them into a larger multi-agent clinical or research workflow.
