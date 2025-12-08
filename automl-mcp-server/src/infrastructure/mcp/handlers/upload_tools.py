"""
Dataset Upload Tools for MCP

Provides interactive file upload workflow with TWO storage modes:

1. TEMPORARY (Redis) - 暫存模式
   - Data stored in Redis (with job)
   - For one-time analysis
   - Auto-expires after job completion
   - Faster, no MinIO overhead
   
2. PERMANENT (MinIO) - 永久存檔
   - Data stored in MinIO
   - Can be reused for multiple analyses
   - Requires dataset registration
   - Best for ML training and repeated analysis

Architecture Decision:
- Copilot should NOT read file content (wastes tokens, truncation risk)
- MCP Server reads files directly via volume mount
- Supports both local files and MinIO paths
"""
import base64
import logging
import os
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient
from .stats_client import StatsClient

logger = logging.getLogger(__name__)

# Data directories mounted in container
# These paths are inside the container, mapped from host
DATA_MOUNT_PATHS = [
    "/data/sample_data",    # ./sample_data:/data/sample_data
    "/data/uploads",        # ./uploads:/data/uploads
    "/data/datasets",       # ./datasets:/data/datasets (if exists)
]


def register_upload_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register dataset upload tools"""
    
    stats_client = StatsClient()

    @mcp.tool()
    async def list_available_files(
        directory: Annotated[Optional[str], Field(
            description="Directory to list. If not provided, lists all mounted data directories."
        )] = None,
        pattern: Annotated[str, Field(
            description="File pattern to match (e.g., '*.csv')"
        )] = "*.csv",
    ) -> Dict[str, Any]:
        """
        📂 List available files in mounted data directories.
        
        Use this BEFORE upload_dataset to see what LOCAL files are available.
        
        Mounted directories:
        - /data/sample_data - Sample datasets for testing
        - /data/uploads - User uploaded files
        - /data/datasets - Additional datasets
        
        Note: This only shows LOCAL files. For registered datasets (in MinIO),
        use list_datasets() instead.
        
        Returns:
            directories: List of available directories
            files: List of files matching pattern
            total_count: Total number of files found
            
        Example:
            # List all CSV files
            list_available_files()
            
            # List files in specific directory
            list_available_files(directory="/data/sample_data")
        """
        result = {
            "directories": [],
            "files": [],
            "total_count": 0,
        }
        
        search_dirs = [directory] if directory else DATA_MOUNT_PATHS
        
        for dir_path in search_dirs:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                result["directories"].append(str(path))
                for file_path in path.glob(pattern):
                    if file_path.is_file():
                        stat = file_path.stat()
                        result["files"].append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "size_bytes": stat.st_size,
                            "size_human": _format_size(stat.st_size),
                        })
        
        result["total_count"] = len(result["files"])
        result["files"].sort(key=lambda x: x["name"])
        
        return result

    @mcp.tool()
    async def upload_dataset(
        name: Annotated[str, Field(description="Dataset name for identification")],
        user_id: Annotated[str, Field(description="User ID for resource isolation")],
        source_type: Annotated[str, Field(
            description="Upload source: 'local' (file in mounted directory) or 'minio' (existing MinIO path)"
        )],
        source_path: Annotated[str, Field(
            description="For 'local': file path (e.g., '/data/sample_data/iris.csv'). "
                       "For 'minio': MinIO path (e.g., 'bucket/path/file.csv')"
        )],
        storage_mode: Annotated[str, Field(
            description="Storage mode: 'temporary' (Redis, one-time use) or 'permanent' (MinIO, reusable)"
        )] = "permanent",
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        description: Annotated[Optional[str], Field(description="Optional dataset description")] = None,
    ) -> Dict[str, Any]:
        """
        📤 Upload a dataset for analysis or ML training.
        
        ⚠️ IMPORTANT: Ask user TWO questions BEFORE calling:
        1. Which FILE to use? (local or MinIO)
        2. Save permanently or temporary use only?
        
        STORAGE MODES:
        
        🔄 TEMPORARY (storage_mode='temporary'):
           - Stored in Redis with the job
           - For one-time analysis only
           - Faster, no MinIO overhead
           - Data expires after job completion
           - Returns: job_id (use for analysis)
        
        💾 PERMANENT (storage_mode='permanent'):  
           - Stored in MinIO
           - Can be reused for multiple analyses
           - Required for ML training
           - Returns: dataset_id (use for training/analysis)
        
        Workflow:
        ```
        Agent: "我來幫你上傳資料集。請回答兩個問題："
        
        Q1: "資料來源？"
            1. 📁 本地檔案 (sample_data, uploads 資料夾)
            2. ☁️ MinIO 路徑 (已在 MinIO 的檔案)
        
        Q2: "儲存方式？"
            1. 🔄 暫存 (一次性分析，不保留)
            2. 💾 永久存檔 (可重複使用，用於 ML 訓練)
        
        User: "本地檔案 breast_cancer.csv，暫存"
        
        Agent: upload_dataset(
                 name="breast_cancer",
                 source_type="local",
                 source_path="/data/sample_data/breast_cancer.csv",
                 storage_mode="temporary"
               )
        ```
        
        Returns:
            For TEMPORARY:
                job_id: Use this for direct analysis
                data_preview: Sample of the data
                next_steps: How to analyze the data
                
            For PERMANENT:
                dataset_id: Use this for training/analysis
                columns: List of column names
                row_count: Number of rows
                next_steps: How to use the dataset
        """
        try:
            # Validate storage_mode
            if storage_mode not in ("temporary", "permanent"):
                return {
                    "success": False,
                    "error": f"Invalid storage_mode: {storage_mode}",
                    "hint": "Use 'temporary' (暫存) or 'permanent' (永久存檔)",
                }
            
            # Read file content based on source_type
            if source_type == "local":
                file_result = _read_local_file(source_path)
                if not file_result["success"]:
                    return file_result
                csv_content = file_result["content"]
                
            elif source_type == "minio":
                # For MinIO source with permanent storage, just register
                if storage_mode == "permanent":
                    return await _register_minio_dataset(
                        client, name, source_path, user_id, session_id, description
                    )
                else:
                    # For temporary, need to read from MinIO first
                    # This is less common, user should use permanent for MinIO
                    return {
                        "success": False,
                        "error": "MinIO source with temporary storage is not recommended",
                        "hint": "For MinIO files, use storage_mode='permanent'. "
                               "For temporary analysis, use local files.",
                    }
            else:
                return {
                    "success": False,
                    "error": f"Invalid source_type: {source_type}",
                    "hint": "Use 'local' or 'minio'",
                }
            
            # Route to appropriate storage
            if storage_mode == "temporary":
                return await _upload_temporary(
                    stats_client, name, csv_content, user_id, session_id, source_path
                )
            else:  # permanent
                return await _upload_permanent(
                    client, name, csv_content, user_id, session_id, description, source_path
                )
                
        except Exception as e:
            logger.exception(f"Upload failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "hint": "Check if file exists and is accessible.",
            }

    @mcp.tool()
    async def get_upload_help() -> Dict[str, Any]:
        """
        ❓ Get help on how to upload datasets.
        
        Call this when user asks about uploading files or data.
        Returns instructions for the upload workflow.
        """
        return {
            "title": "📤 Dataset Upload Guide",
            "description": "上傳資料集有兩種儲存模式，請先確認需求",
            "questions_to_ask": [
                {
                    "question": "Q1: 資料來源？",
                    "options": [
                        "📁 本地檔案 (source_type='local') - 從 sample_data, uploads 資料夾",
                        "☁️ MinIO 路徑 (source_type='minio') - 已存在 MinIO 的檔案",
                    ],
                },
                {
                    "question": "Q2: 儲存方式？",
                    "options": [
                        "🔄 暫存 (storage_mode='temporary') - 一次性分析，處理完自動清除",
                        "💾 永久存檔 (storage_mode='permanent') - 存入 MinIO，可重複使用",
                    ],
                },
            ],
            "storage_comparison": {
                "temporary": {
                    "storage": "Redis (隨 job 存放)",
                    "lifetime": "Job 完成後過期",
                    "use_case": "一次性統計分析、快速探索",
                    "returns": "job_id",
                    "next_tool": "get_stats_job_result(job_id)",
                },
                "permanent": {
                    "storage": "MinIO (永久保存)",
                    "lifetime": "直到手動刪除",
                    "use_case": "ML 訓練、重複分析、長期保存",
                    "returns": "dataset_id",
                    "next_tool": "submit_automl_job(dataset_id) 或 auto_analyze(dataset_id)",
                },
            },
            "workflow_example": """
Agent: "我來幫你上傳資料。請問："
Agent: "1️⃣ 資料來源：本地檔案還是 MinIO？"
User:  "本地"
Agent: list_available_files()  # 列出可用檔案
Agent: "2️⃣ 儲存方式：暫存（一次性）還是永久存檔？"
User:  "永久存檔，要做 ML 訓練"
Agent: upload_dataset(
         name="my_data",
         source_type="local",
         source_path="/data/sample_data/breast_cancer.csv",
         storage_mode="permanent"
       )
""",
        }


def _read_local_file(file_path: str) -> Dict[str, Any]:
    """Read content from local file (mounted in container)"""
    path = Path(file_path)
    
    # Validate file exists
    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "hint": f"Use list_available_files() to see available files. "
                   f"Mounted directories: {DATA_MOUNT_PATHS}",
        }
    
    if not path.is_file():
        return {
            "success": False,
            "error": f"Not a file: {file_path}",
        }
    
    # Check file size
    file_size = path.stat().st_size
    if file_size > 100 * 1024 * 1024:  # 100MB limit
        return {
            "success": False,
            "error": f"File too large ({_format_size(file_size)}). Max 100MB.",
            "hint": "For large files, upload to MinIO first and use source_type='minio'.",
        }
    
    # Read file content
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = path.read_text(encoding='latin-1')
    
    # Validate CSV
    lines = content.split('\n')
    if len(lines) < 2:
        return {
            "success": False,
            "error": "File appears empty or has no data rows.",
        }
    
    return {
        "success": True,
        "content": content,
        "size": file_size,
    }


async def _upload_temporary(
    stats_client: StatsClient,
    name: str,
    csv_content: str,
    user_id: str,
    session_id: Optional[str],
    source_path: str,
) -> Dict[str, Any]:
    """Upload to Redis for temporary/one-time analysis"""
    
    # Call stats-service direct analyze endpoint
    result = await stats_client.direct_analyze(
        csv_content=csv_content,
        user_id=user_id,
        session_id=session_id,
    )
    
    return {
        "success": True,
        "storage_mode": "temporary",
        "job_id": result.get("job_id"),
        "job_type": result.get("job_type"),
        "status": result.get("status"),
        "data_preview": result.get("data_preview"),
        "source": {
            "type": "local",
            "path": source_path,
            "name": name,
        },
        "next_steps": [
            f"Job submitted with ID: {result.get('job_id')}",
            "Check status: get_stats_job_status(job_id)",
            "Get results: get_stats_job_result(job_id)",
            "⚠️ Data is temporary - will be cleared after job completion",
        ],
    }


async def _upload_permanent(
    client: AutoMLClient,
    name: str,
    csv_content: str,
    user_id: str,
    session_id: Optional[str],
    description: Optional[str],
    source_path: str,
) -> Dict[str, Any]:
    """Upload to MinIO for permanent storage"""
    
    result = await client.upload_csv_content(
        name=name,
        csv_content=csv_content,
        user_id=user_id,
        session_id=session_id,
        description=description or f"Uploaded from {Path(source_path).name}",
    )
    
    return {
        "success": True,
        "storage_mode": "permanent",
        "dataset_id": result.get("dataset_id"),
        "name": result.get("name"),
        "minio_path": result.get("minio_path"),
        "columns": result.get("columns"),
        "row_count": result.get("row_count"),
        "source": {
            "type": "local",
            "path": source_path,
        },
        "next_steps": [
            f"Dataset registered with ID: {result.get('dataset_id')}",
            "For ML training: submit_automl_job(dataset_id=..., target_column='...')",
            "For statistics: auto_analyze(dataset_id=...) or submit_tableone_job(...)",
            "For preview: preview_dataset_stats(dataset_id=...)",
            "💾 Data saved permanently in MinIO",
        ],
    }


async def _register_minio_dataset(
    client: AutoMLClient,
    name: str,
    minio_path: str,
    user_id: str,
    session_id: Optional[str],
    description: Optional[str],
) -> Dict[str, Any]:
    """Register existing MinIO file as dataset"""
    
    result = await client.register_dataset(
        name=name,
        minio_path=minio_path,
        user_id=user_id,
        session_id=session_id,
        description=description,
    )
    
    return {
        "success": True,
        "storage_mode": "permanent",
        "dataset_id": result.get("dataset_id"),
        "name": result.get("name"),
        "minio_path": minio_path,
        "columns": result.get("columns"),
        "row_count": result.get("row_count"),
        "source": {
            "type": "minio",
            "path": minio_path,
        },
        "next_steps": [
            f"Dataset registered with ID: {result.get('dataset_id')}",
            "For ML training: submit_automl_job(dataset_id=..., target_column='...')",
            "For statistics: auto_analyze(dataset_id=...) or submit_tableone_job(...)",
        ],
    }


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
