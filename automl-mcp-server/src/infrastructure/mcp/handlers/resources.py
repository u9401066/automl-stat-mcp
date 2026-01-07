"""
MCP Resources for AutoML

Resources are read-only information endpoints that don't require tool invocation.
They provide static or cached information to AI agents.

Resources vs Tools:
- Resources: GET-like, no side effects, fast, cacheable
- Tools: POST-like, may have side effects, may be slow

Available Resources:
- automl://algorithms - List of available ML algorithms
- automl://health - Service health status
- automl://help/upload - Upload workflow documentation
- automl://help/paths - Path resolution guide
- automl://files/{directory} - List files in directory

Created: 2025-12-16
"""
import json
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# =============================================================================
# STATIC DATA
# =============================================================================

ALGORITHMS_INFO = {
    "algorithms": {
        "GBM": {"name": "LightGBM", "type": "gradient_boosting", "speed": "fast"},
        "CAT": {"name": "CatBoost", "type": "gradient_boosting", "speed": "medium"},
        "XGB": {"name": "XGBoost", "type": "gradient_boosting", "speed": "medium"},
        "RF": {"name": "Random Forest", "type": "ensemble", "speed": "fast"},
        "XT": {"name": "Extra Trees", "type": "ensemble", "speed": "fast"},
        "KNN": {"name": "K-Nearest Neighbors", "type": "instance_based", "speed": "fast"},
        "LR": {"name": "Linear/Logistic Regression", "type": "linear", "speed": "very_fast"},
        "NN_TORCH": {"name": "Neural Network (PyTorch)", "type": "neural_network", "speed": "slow"},
        "FASTAI": {"name": "FastAI", "type": "neural_network", "speed": "slow"},
    },
    "recommended": {
        "quick": ["GBM", "RF", "LR"],
        "best_quality": ["XGB", "CAT", "GBM", "NN_TORCH"],
        "interpretable": ["LR", "RF"],
    },
    "usage": "Use algorithm codes in submit_specific_job(algorithms=['XGB', 'RF'])"
}

PATH_RESOLUTION_GUIDE = """
# MCP Path Resolution Guide

## Golden Rule
**All MCP tool csv_path parameters use Container paths starting with /data/**

## Path Conversion Table

| User Input | Container Path |
|------------|----------------|
| `iris.csv` | `/data/sample_data/iris.csv` |
| `sample_data/xxx.csv` | `/data/sample_data/xxx.csv` |
| `projects/study1/data.csv` | `/data/projects/study1/data.csv` |
| `/home/user/.../sample_data/xxx.csv` | `/data/sample_data/xxx.csv` |

## Available Directories

| Directory | Description | Access |
|-----------|-------------|--------|
| `/data/sample_data/` | Sample datasets for testing | Read-only |
| `/data/projects/` | User research projects | Read-write |
| `/data/uploads/` | Uploaded files | Read-write |

## Integrated Tools (Automatic Resolution)

These tools handle path resolution automatically:
- `smart_analyze(csv_path="iris.csv")` ✅
- `quick_preview(csv_path="sample_data/heart.csv")` ✅
- `analyze_medical_study(csv_path="medical_study.csv")` ✅

## Legacy Tools (Manual Path Required)

These tools require explicit /data/ paths:
- `get_quick_stats(csv_path="/data/sample_data/iris.csv")`
- `generate_tableone_directly(csv_path="/data/sample_data/titanic.csv")`
"""

UPLOAD_HELP = """
# Dataset Upload Workflow

## Quick Decision Tree

```
Do you want to reuse this data later?
├─ YES → storage_mode="permanent" (stored in MinIO)
└─ NO  → storage_mode="temporary" (one-time analysis)
```

## Upload Methods

### Method 1: Local File (Recommended)

```python
upload_dataset(
    name="my_study",
    source_type="local",
    source_path="/data/sample_data/my_file.csv",  # Container path
    storage_mode="temporary",  # or "permanent"
    user_id="eric"
)
```

### Method 2: Already in MinIO

```python
upload_dataset(
    name="my_study",
    source_type="minio",
    source_path="bucket/path/file.csv",
    user_id="eric"
)
```

## After Upload

- **Temporary**: Use `job_id` for immediate analysis
- **Permanent**: Use `dataset_id` for training and analysis

## Quick Analysis Shortcut

Skip upload for simple analysis:
```python
smart_analyze(csv_path="iris.csv")  # Auto-resolves path
```
"""


def register_resources(mcp: FastMCP, automl_client) -> None:
    """Register MCP resources"""

    # ==========================================================================
    # ALGORITHMS RESOURCE
    # ==========================================================================

    @mcp.resource("automl://algorithms")
    async def get_algorithms_resource() -> str:
        """
        List of available ML algorithms.

        Returns JSON with:
        - algorithms: Dict of algorithm codes and info
        - recommended: Suggested algorithms for different use cases
        - usage: How to use in training
        """
        return json.dumps(ALGORITHMS_INFO, indent=2)

    # ==========================================================================
    # HEALTH RESOURCE
    # ==========================================================================

    @mcp.resource("automl://health")
    async def get_health_resource() -> str:
        """
        Service health status.

        Checks:
        - AutoML API connectivity
        - Stats service connectivity
        - Redis connectivity (if available)
        """
        try:
            health = await automl_client.health_check()
            return json.dumps({
                "status": "healthy",
                "automl_api": health,
                "timestamp": __import__("datetime").datetime.utcnow().isoformat()
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "unhealthy",
                "error": str(e)
            }, indent=2)

    # ==========================================================================
    # HELP RESOURCES
    # ==========================================================================

    @mcp.resource("automl://help/upload")
    async def get_upload_help_resource() -> str:
        """Upload workflow documentation"""
        return UPLOAD_HELP

    @mcp.resource("automl://help/paths")
    async def get_paths_help_resource() -> str:
        """Path resolution guide"""
        return PATH_RESOLUTION_GUIDE

    # ==========================================================================
    # FILES RESOURCE (Dynamic)
    # ==========================================================================

    @mcp.resource("automl://files/sample_data")
    async def get_sample_data_files() -> str:
        """List files in /data/sample_data/"""
        try:
            path = Path("/data/sample_data")
            if not path.exists():
                return json.dumps({"error": "Directory not found", "path": str(path)})

            files = []
            for f in path.glob("*.csv"):
                stat = f.stat()
                files.append({
                    "name": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "path": str(f),
                })

            return json.dumps({
                "directory": str(path),
                "file_count": len(files),
                "files": sorted(files, key=lambda x: x["name"])
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @mcp.resource("automl://files/projects")
    async def get_projects_files() -> str:
        """List files in /data/projects/"""
        try:
            path = Path("/data/projects")
            if not path.exists():
                return json.dumps({"error": "Directory not found", "path": str(path)})

            projects = []
            for p in path.iterdir():
                if p.is_dir():
                    csv_files = list(p.rglob("*.csv"))
                    projects.append({
                        "name": p.name,
                        "csv_count": len(csv_files),
                        "files": [str(f.relative_to(path)) for f in csv_files[:5]],
                    })

            return json.dumps({
                "directory": str(path),
                "project_count": len(projects),
                "projects": projects
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # ==========================================================================
    # DEFAULT USER RESOURCE
    # ==========================================================================

    @mcp.resource("automl://config/defaults")
    async def get_defaults_resource() -> str:
        """Default configuration values"""
        return json.dumps({
            "user_id": os.getenv("DEFAULT_USER_ID", "eric"),
            "storage_mode": "temporary",
            "pval": True,
            "n_rows_preview": 10,
            "correlation_method": "auto",
        }, indent=2)

    logger.info("MCP Resources registered: algorithms, health, help/upload, help/paths, files/*, config/defaults")
