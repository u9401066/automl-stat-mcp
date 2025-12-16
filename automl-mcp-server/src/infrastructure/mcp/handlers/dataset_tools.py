"""
Dataset Tools for MCP

Tools for managing datasets (register, list, delete).
"""
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient


def register_dataset_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register all dataset management tools"""

    @mcp.tool()
    async def register_dataset(
        name: Annotated[str, Field(description="Dataset name for identification")],
        minio_path: Annotated[str, Field(description="Path to CSV file in MinIO (e.g., 'bucket/path/file.csv')")],
        user_id: Annotated[str, Field(description="User ID for resource isolation")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
        description: Annotated[Optional[str], Field(description="Optional dataset description")] = None,
    ) -> Dict[str, Any]:
        """
        Register a CSV dataset from MinIO for use in training.

        The file must already exist in MinIO. This validates the file
        and registers it with the AutoML service.

        Returns:
            dataset_id: Unique identifier for this dataset
            name: Dataset name
            columns: List of column names
            row_count: Number of rows

        Next step: Use dataset_id in submit_automl_job or submit_specific_job
        """
        return await client.register_dataset(
            name=name,
            minio_path=minio_path,
            user_id=user_id,
            session_id=session_id,
            description=description,
        )

    @mcp.tool()
    async def list_datasets(
        user_id: Annotated[str, Field(description="User ID")],
        session_id: Annotated[Optional[str], Field(description="Optional session ID")] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all datasets registered by the user.

        Returns:
            List of datasets with their IDs, names, columns, and metadata
        """
        return await client.list_datasets(user_id, session_id)

    @mcp.tool()
    async def delete_dataset(
        dataset_id: Annotated[str, Field(description="Dataset ID to delete")],
        user_id: Annotated[str, Field(description="User ID")],
    ) -> Dict[str, Any]:
        """
        Delete a registered dataset.

        Note: This only removes the registration, not the file in MinIO.
        """
        return await client.delete_dataset(dataset_id, user_id)
