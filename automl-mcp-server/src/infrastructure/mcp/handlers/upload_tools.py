"""
Dataset Upload Tools for MCP

Provides interactive file upload workflow:
1. Agent calls upload_dataset
2. MCP prompts user to choose upload method
3. User selects: local file path OR MinIO path
4. MCP executes upload and verifies success
5. Returns dataset_id with next steps

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
        
        Use this BEFORE upload_dataset to see what files are available.
        
        Mounted directories:
        - /data/sample_data - Sample datasets for testing
        - /data/uploads - User uploaded files
        - /data/datasets - Additional datasets
        
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
            description="Upload source type: 'local' (file in mounted directory) or 'minio' (existing MinIO path)"
        )],
        source_path: Annotated[str, Field(
            description="For 'local': file path in container (e.g., '/data/sample_data/breast_cancer.csv'). "
                       "For 'minio': MinIO path (e.g., 'bucket/path/file.csv')"
        )],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        description: Annotated[Optional[str], Field(description="Optional dataset description")] = None,
    ) -> Dict[str, Any]:
        """
        📤 Upload a dataset for ML training or statistical analysis.
        
        ⚠️ IMPORTANT: Ask user which source type to use BEFORE calling this tool!
        
        Two upload methods:
        
        1. LOCAL FILE (source_type='local'):
           - File must be in a mounted directory (/data/sample_data, /data/uploads)
           - Use list_available_files() first to see available files
           - MCP Server reads file directly (NO token waste!)
           
        2. MINIO PATH (source_type='minio'):
           - File already exists in MinIO storage
           - Just registers the reference, no data transfer
        
        Workflow:
        ```
        Agent: "I'll help you upload the dataset. How would you like to provide it?"
        
        Option 1 - Local file:
          → Use list_available_files() to show available files
          → User picks a file
          → Call upload_dataset(source_type='local', source_path='/data/...')
        
        Option 2 - MinIO:
          → User provides MinIO path
          → Call upload_dataset(source_type='minio', source_path='bucket/...')
        ```
        
        Returns:
            success: Whether upload succeeded
            dataset_id: Unique ID for this dataset (use in subsequent operations)
            name: Dataset name
            columns: List of column names
            row_count: Number of rows
            source: Where the data came from
            next_steps: Suggested next actions
            
        Example:
            # Local file upload
            upload_dataset(
                name="breast_cancer",
                user_id="user1",
                source_type="local",
                source_path="/data/sample_data/breast_cancer.csv"
            )
            
            # MinIO reference
            upload_dataset(
                name="my_data",
                user_id="user1", 
                source_type="minio",
                source_path="datasets/my_data.csv"
            )
        """
        try:
            if source_type == "local":
                return await _upload_from_local(
                    client, name, source_path, user_id, session_id, description
                )
            elif source_type == "minio":
                return await _upload_from_minio(
                    client, name, source_path, user_id, session_id, description
                )
            else:
                return {
                    "success": False,
                    "error": f"Invalid source_type: {source_type}. Use 'local' or 'minio'.",
                    "hint": "Ask user: Do you want to use a local file or MinIO path?",
                }
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
        Returns instructions for the two upload methods.
        """
        return {
            "title": "Dataset Upload Guide",
            "methods": [
                {
                    "name": "Local File",
                    "source_type": "local",
                    "description": "Upload from files in mounted directories",
                    "steps": [
                        "1. Call list_available_files() to see available files",
                        "2. User selects a file",
                        "3. Call upload_dataset(source_type='local', source_path='...')",
                    ],
                    "mounted_directories": DATA_MOUNT_PATHS,
                    "example": "upload_dataset(name='my_data', user_id='user1', "
                              "source_type='local', source_path='/data/sample_data/iris.csv')",
                },
                {
                    "name": "MinIO Storage",
                    "source_type": "minio",
                    "description": "Reference existing file in MinIO",
                    "steps": [
                        "1. User provides MinIO path (bucket/path/file.csv)",
                        "2. Call upload_dataset(source_type='minio', source_path='...')",
                    ],
                    "example": "upload_dataset(name='my_data', user_id='user1', "
                              "source_type='minio', source_path='datasets/file.csv')",
                },
            ],
            "ask_user": "Which method would you like to use?\n"
                       "1. 📁 Local file (from sample_data or uploads folder)\n"
                       "2. ☁️ MinIO path (file already in MinIO storage)",
        }


async def _upload_from_local(
    client: AutoMLClient,
    name: str,
    file_path: str,
    user_id: str,
    session_id: Optional[str],
    description: Optional[str],
) -> Dict[str, Any]:
    """Upload from local file (mounted in container)"""
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
    if file_size > 100 * 1024 * 1024:  # 100MB limit for direct upload
        return {
            "success": False,
            "error": f"File too large ({_format_size(file_size)}). Max 100MB for direct upload.",
            "hint": "For large files, upload to MinIO first and use source_type='minio'.",
        }
    
    # Read file content
    try:
        content = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try with different encoding
        content = path.read_text(encoding='latin-1')
    
    # Validate it looks like CSV
    lines = content.split('\n')
    if len(lines) < 2:
        return {
            "success": False,
            "error": "File appears empty or has no data rows.",
        }
    
    # Upload via automl-service direct endpoint
    # The service will store it in MinIO and register it
    result = await client.upload_csv_content(
        name=name,
        csv_content=content,
        user_id=user_id,
        session_id=session_id,
        description=description or f"Uploaded from {path.name}",
    )
    
    # Add metadata
    result["success"] = True
    result["source"] = {
        "type": "local",
        "path": file_path,
        "size": _format_size(file_size),
    }
    result["next_steps"] = [
        f"Dataset registered with ID: {result.get('dataset_id', 'N/A')}",
        "For ML training: submit_automl_job(dataset_id=..., target_column='...')",
        "For statistics: auto_analyze(dataset_id=...) or submit_tableone_job(...)",
        "For preview: preview_dataset_stats(dataset_id=...)",
    ]
    
    return result


async def _upload_from_minio(
    client: AutoMLClient,
    name: str,
    minio_path: str,
    user_id: str,
    session_id: Optional[str],
    description: Optional[str],
) -> Dict[str, Any]:
    """Register dataset from existing MinIO path"""
    result = await client.register_dataset(
        name=name,
        minio_path=minio_path,
        user_id=user_id,
        session_id=session_id,
        description=description,
    )
    
    result["success"] = True
    result["source"] = {
        "type": "minio",
        "path": minio_path,
    }
    result["next_steps"] = [
        f"Dataset registered with ID: {result.get('dataset_id', 'N/A')}",
        "For ML training: submit_automl_job(dataset_id=..., target_column='...')",
        "For statistics: auto_analyze(dataset_id=...) or submit_tableone_job(...)",
        "For preview: preview_dataset_stats(dataset_id=...)",
    ]
    
    return result


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
