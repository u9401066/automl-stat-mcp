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

import logging
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient
from .stats_client import StatsClient

logger = logging.getLogger(__name__)

# Data directories mounted in container
# Only sample_data (public test data) and projects (user research projects)
# All temp data goes to Redis, permanent results go to MinIO
DATA_MOUNT_PATHS = [
    "/data/sample_data",  # ./sample_data:/data/sample_data (read-only)
    "/data/projects",  # ./projects:/data/projects (read-write)
]

# Token limit for data preview (prevent response bloat)
MAX_PREVIEW_VALUE_LENGTH = 50  # Truncate cell values longer than this
MAX_PREVIEW_ROWS = 2  # Only show 2 sample rows
MAX_PREVIEW_COLUMNS = 10  # Only show first N columns in sample rows


def _sanitize_column_name(name: str) -> str:
    """
    Sanitize column name for safe usage in analysis.

    Rules:
    1. Replace special chars with underscore
    2. Remove leading/trailing whitespace
    3. Replace multiple spaces/underscores with single underscore
    4. Handle Chinese characters (keep them)
    5. Remove problematic chars: ()[]{}:;,./\\|!@#$%^&*+=
    6. Handle Excel duplicate suffixes like .1, .2
    """
    import re

    if not name or not isinstance(name, str):
        return "unnamed"

    original = name.strip()

    # Handle "Unnamed: X" from Excel
    if original.lower().startswith("unnamed:"):
        return f"col_{original.split(':')[-1].strip()}"

    # Replace special characters with underscore (keep Chinese, alphanumeric)
    # Pattern: keep Chinese (\u4e00-\u9fff), letters, numbers, underscore
    sanitized = re.sub(r"[^\w\u4e00-\u9fff]", "_", original)

    # Replace multiple underscores with single
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # If empty after sanitization, use hash of original
    if not sanitized:
        sanitized = f"col_{abs(hash(original)) % 10000}"

    return sanitized


def _create_column_mapping(original_columns: List[str]) -> Dict[str, Any]:
    """
    Create mapping from original column names to sanitized names.

    Returns:
        {
            "mapping": {original: sanitized, ...},
            "reverse_mapping": {sanitized: original, ...},
            "changed_columns": [(original, sanitized), ...],  # only changed ones
            "unchanged_columns": [name, ...],
        }
    """
    mapping = {}
    reverse_mapping = {}
    changed = []
    unchanged = []

    # Track used names to handle duplicates
    used_names = {}

    for orig in original_columns:
        sanitized = _sanitize_column_name(orig)

        # Handle duplicates by adding suffix
        if sanitized in used_names:
            used_names[sanitized] += 1
            sanitized = f"{sanitized}_{used_names[sanitized]}"
        else:
            used_names[sanitized] = 0

        mapping[orig] = sanitized
        reverse_mapping[sanitized] = orig

        if orig != sanitized:
            changed.append((orig, sanitized))
        else:
            unchanged.append(orig)

    return {
        "mapping": mapping,
        "reverse_mapping": reverse_mapping,
        "changed_columns": changed,
        "unchanged_columns": unchanged,
        "total_columns": len(original_columns),
        "columns_renamed": len(changed),
    }


def _process_csv_in_memory(
    csv_content: str,
    original_name: str,
) -> Dict[str, Any]:
    """
    Process CSV in memory: sanitize column names, return processed content.

    NO LOCAL FILE STORAGE - all data stays in memory or goes to Redis/MinIO.

    Returns:
        {
            "processed_content": cleaned CSV as string,
            "column_mapping": mapping dict,
            "sanitized_columns": list of new column names,
            "row_count": number of rows,
            "column_count": number of columns,
        }
    """
    from io import StringIO

    import pandas as pd

    # Read original CSV
    df = pd.read_csv(StringIO(csv_content))
    original_columns = list(df.columns)

    # Create column mapping
    column_mapping = _create_column_mapping(original_columns)

    # Rename columns
    df.columns = [column_mapping["mapping"][col] for col in original_columns]

    # Convert back to CSV string (in memory, no file write)
    processed_content = df.to_csv(index=False)

    return {
        "processed_content": processed_content,
        "column_mapping": column_mapping,
        "sanitized_columns": list(df.columns),
        "row_count": len(df),
        "column_count": len(df.columns),
    }


def _truncate_value(value: Any, max_length: int = MAX_PREVIEW_VALUE_LENGTH) -> Any:
    """Truncate string values that exceed max_length"""
    if value is None:
        return None
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    return value


def _truncate_row(row: Dict[str, Any], max_columns: int = MAX_PREVIEW_COLUMNS) -> Dict[str, Any]:
    """Truncate row: limit columns and truncate values"""
    truncated = {}
    for i, (k, v) in enumerate(row.items()):
        if i >= max_columns:
            truncated["..."] = f"(+{len(row) - max_columns} more columns)"
            break
        truncated[k] = _truncate_value(v)
    return truncated


def _create_data_preview(data_preview: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create minimal data preview for Agent confirmation.

    Returns:
        - rows: total row count
        - column_count: total column count
        - column_names: FULL list of column names
        - sample_rows: 2 rows with truncated values (confirm data received)
    """
    sample_rows = data_preview.get("sample_rows", [])
    column_names = data_preview.get("column_names", [])

    # Truncate sample rows (max 2 rows, max 10 columns, truncated values)
    truncated_samples = [_truncate_row(row) for row in sample_rows[:MAX_PREVIEW_ROWS]]

    return {
        "rows": data_preview.get("rows"),
        "column_count": data_preview.get("columns"),  # count
        "column_names": column_names,  # FULL list
        "sample_rows": truncated_samples,  # 2 rows, 10 columns, truncated values
    }


def register_upload_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register dataset upload tools"""

    stats_client = StatsClient()

    @mcp.tool()
    async def list_available_files(
        directory: Annotated[
            Optional[str], Field(description="Directory to list. If not provided, lists all mounted data directories.")
        ] = None,
        pattern: Annotated[str, Field(description="File pattern to match (e.g., '*.csv')")] = "*.csv",
    ) -> Dict[str, Any]:
        """
        📂 List available files in mounted data directories.

        Use this BEFORE upload_dataset to see what LOCAL files are available.

        Mounted directories:
        - /data/sample_data - Sample datasets for testing (read-only)
        - /data/projects - User research projects (read-write)

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
                        result["files"].append(
                            {
                                "path": str(file_path),
                                "name": file_path.name,
                                "size_bytes": stat.st_size,
                                "size_human": _format_size(stat.st_size),
                            }
                        )

        result["total_count"] = len(result["files"])
        result["files"].sort(key=lambda x: x["name"])

        return result

    @mcp.tool()
    async def upload_dataset(
        name: Annotated[str, Field(description="Dataset name for identification")],
        user_id: Annotated[str, Field(description="User ID for resource isolation")],
        source_type: Annotated[
            str,
            Field(description="Upload source: 'local' (file in mounted directory) or 'minio' (existing MinIO path)"),
        ],
        source_path: Annotated[
            str,
            Field(
                description="For 'local': file path (e.g., '/data/sample_data/iris.csv'). "
                "For 'minio': MinIO path (e.g., 'bucket/path/file.csv')"
            ),
        ],
        storage_mode: Annotated[
            str, Field(description="Storage mode: 'temporary' (Redis, one-time use) or 'permanent' (MinIO, reusable)")
        ] = "permanent",
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
                    return await _register_minio_dataset(client, name, source_path, user_id, session_id, description)
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
                return await _upload_temporary(stats_client, name, csv_content, user_id, session_id, source_path)
            else:  # permanent
                return await _upload_permanent(client, name, csv_content, user_id, session_id, description, source_path)

        except Exception as e:
            logger.exception(f"Upload failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "hint": "Check if file exists and is accessible.",
            }

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
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
            "hint": f"Use list_available_files() to see available files. Mounted directories: {DATA_MOUNT_PATHS}",
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
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = path.read_text(encoding="latin-1")

    # Validate CSV
    lines = content.split("\n")
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
    """Upload to Redis for temporary/one-time analysis with column sanitization.

    NO LOCAL FILE STORAGE - all data processed in memory, stored in Redis with TTL.
    """

    try:
        # Process CSV in memory: sanitize columns
        processed = _process_csv_in_memory(
            csv_content=csv_content,
            original_name=name,
        )

        # Call stats-service with processed (clean) data - stored in Redis with TTL
        result = await stats_client.direct_analyze(
            csv_content=processed["processed_content"],
            user_id=user_id,
        )

        # Create minimal preview (full column_names + 2 truncated sample rows)
        data_preview = _create_data_preview(result.get("data_preview", {}))

        # Build column rename summary for Agent
        column_mapping = processed["column_mapping"]
        rename_summary = []
        for orig, new in column_mapping["changed_columns"][:10]:  # Show first 10
            rename_summary.append(f"'{orig}' → '{new}'")
        if len(column_mapping["changed_columns"]) > 10:
            rename_summary.append(f"... (+{len(column_mapping['changed_columns']) - 10} more)")

        return {
            "success": True,
            "storage_mode": "temporary",
            "job_id": result.get("job_id"),
            "job_type": result.get("job_type"),
            "status": result.get("status"),
            "data_preview": data_preview,
            # Column processing info (no file paths - all in memory/Redis)
            "column_processing": {
                "columns_renamed": column_mapping["columns_renamed"],
                "total_columns": column_mapping["total_columns"],
                "rename_examples": rename_summary if rename_summary else None,
                "sanitized_columns": processed["sanitized_columns"],
            },
            "source": {
                "type": "local",
                "path": source_path,
                "name": name,
            },
            "next_steps": [
                f"Job submitted with ID: {result.get('job_id')}",
                "Check status: get_stats_job_status(job_id)",
                "Get results: get_stats_job_result(job_id)",
                "📊 Use sanitized column names for analysis (see column_processing.sanitized_columns)",
                "⚠️ Data is temporary in Redis - auto-expires after 24h",
            ],
        }
    except Exception as e:
        logger.error(f"Error in _upload_temporary: {e}")
        return {
            "success": False,
            "error": str(e),
            "hint": "Failed to process CSV. Check file format and encoding.",
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
    """Upload to MinIO for permanent storage with column sanitization.

    NO LOCAL FILE STORAGE - processed in memory, uploaded directly to MinIO.
    """

    try:
        # Process CSV in memory: sanitize columns
        processed = _process_csv_in_memory(
            csv_content=csv_content,
            original_name=name,
        )

        # Upload processed (clean) data directly to MinIO
        result = await client.upload_csv_content(
            name=name,
            csv_content=processed["processed_content"],
            user_id=user_id,
            session_id=session_id,
            description=description or f"Uploaded from {Path(source_path).name} (columns sanitized)",
        )

        # Build column rename summary for Agent
        column_mapping = processed["column_mapping"]
        rename_summary = []
        for orig, new in column_mapping["changed_columns"][:10]:  # Show first 10
            rename_summary.append(f"'{orig}' → '{new}'")
        if len(column_mapping["changed_columns"]) > 10:
            rename_summary.append(f"... (+{len(column_mapping['changed_columns']) - 10} more)")

        return {
            "success": True,
            "storage_mode": "permanent",
            "dataset_id": result.get("dataset_id"),
            "name": result.get("name"),
            "minio_path": result.get("minio_path"),
            "row_count": result.get("row_count"),
            "column_count": len(processed["sanitized_columns"]),
            "column_names": processed["sanitized_columns"],  # Sanitized names
            # Column processing info (no local file paths)
            "column_processing": {
                "columns_renamed": column_mapping["columns_renamed"],
                "total_columns": column_mapping["total_columns"],
                "rename_examples": rename_summary if rename_summary else None,
            },
            "source": {
                "type": "local",
                "path": source_path,
            },
            "next_steps": [
                f"Dataset registered with ID: {result.get('dataset_id')}",
                "For ML training: submit_automl_job(dataset_id=..., target_column='...')",
                "For statistics: auto_analyze(dataset_id=...) or submit_tableone_job(...)",
                "📊 Use sanitized column names (see column_names)",
                "💾 Data saved permanently in MinIO",
            ],
        }
    except Exception as e:
        logger.error(f"Error in _upload_permanent: {e}")
        return {
            "success": False,
            "error": str(e),
            "hint": "Failed to process CSV. Check file format and encoding.",
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

    # Return full column list + count (Agent needs column names for analysis)
    columns = result.get("columns", [])

    return {
        "success": True,
        "storage_mode": "permanent",
        "dataset_id": result.get("dataset_id"),
        "name": result.get("name"),
        "minio_path": minio_path,
        "row_count": result.get("row_count"),
        "column_count": len(columns),
        "column_names": columns,  # FULL list for Agent to select target/features
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
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
