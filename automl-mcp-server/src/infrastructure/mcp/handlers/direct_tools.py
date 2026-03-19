"""
Direct Analysis Tools for MCP

Tools for analyzing data directly without MinIO storage.
Useful for pre-training analysis, testing, and quick exploration.
"""

from typing import Annotated, Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..client import AutoMLClient


def register_direct_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register all direct analysis tools"""

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def direct_ml_analyze(
        csv_content: Annotated[str, Field(description="CSV data as string (can be base64 encoded)")],
        user_id: Annotated[str, Field(description="User ID")],
        is_base64: Annotated[bool, Field(description="Whether csv_content is base64 encoded")] = False,
        target_column: Annotated[Optional[str], Field(description="Target column for ML analysis")] = None,
    ) -> Dict[str, Any]:
        """
        📊 Analyze CSV data directly for ML training preparation.

        This is useful for:
        - Pre-training dataset analysis before uploading to MinIO
        - Quick data exploration without permanent storage
        - Getting ML training recommendations

        The CSV content is passed directly and analyzed synchronously.
        Results include:
        - Dataset shape and structure
        - Target column analysis (if provided)
        - ML training recommendations (presets, time_limit)
        - Data quality warnings

        ⚠️ For large datasets, upload to MinIO first and use analyze_dataset.

        Args:
            csv_content: CSV data as string (or base64 if is_base64=True)
            user_id: User ID
            is_base64: Set True if csv_content is base64 encoded
            target_column: Target column for ML recommendations

        Returns:
            rows: Number of rows
            columns: Number of columns
            column_names: List of column names
            dtypes: Column data types
            target_analysis: Analysis of target column (if provided)
            recommendations: ML training recommendations
            warnings: Data quality warnings
            data_preview: Sample rows

        Example:
            # Analyze before training
            direct_ml_analyze(
                csv_content=\"\"\"age,income,purchased
                30,50000,yes
                25,40000,no
                35,60000,yes\"\"\",
                user_id="user1",
                target_column="purchased"
            )
        """
        return await client.direct_analyze(
            csv_content=csv_content,
            user_id=user_id,
            is_base64=is_base64,
            target_column=target_column,
        )

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def direct_ml_quick_stats(
        csv_content: Annotated[str, Field(description="CSV data as string")],
        user_id: Annotated[str, Field(description="User ID")],
        is_base64: Annotated[bool, Field(description="Whether csv_content is base64 encoded")] = False,
    ) -> Dict[str, Any]:
        """
        ⚡ Get quick statistics for CSV data (synchronous).

        Returns immediately with basic statistics.
        For full ML analysis, use direct_ml_analyze instead.

        Args:
            csv_content: CSV data as string
            user_id: User ID
            is_base64: Set True if base64 encoded

        Returns:
            rows: Number of rows
            columns: Number of columns
            column_info: Type, nulls, unique count per column
            missing_summary: Missing value statistics
            numeric_summary: Basic stats for numeric columns
        """
        return await client.direct_quick_stats(
            csv_content=csv_content,
            user_id=user_id,
            is_base64=is_base64,
        )

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def direct_preview_data(
        csv_content: Annotated[str, Field(description="CSV data as string")],
        user_id: Annotated[str, Field(description="User ID")],
        is_base64: Annotated[bool, Field(description="Whether csv_content is base64 encoded")] = False,
        n_rows: Annotated[int, Field(description="Number of rows to preview (max 100)")] = 10,
    ) -> Dict[str, Any]:
        """
        👀 Preview CSV data before registration.

        Returns the first N rows and basic metadata.
        Useful for verifying data before uploading to MinIO.

        Args:
            csv_content: CSV data as string
            user_id: User ID
            is_base64: Set True if base64 encoded
            n_rows: Number of rows to return (max 100)

        Returns:
            rows: Total row count
            columns: Column count
            column_names: List of column names
            dtypes: Column data types
            preview: First N rows
            missing_values: Missing value count per column
        """
        return await client.direct_preview(
            csv_content=csv_content,
            user_id=user_id,
            is_base64=is_base64,
            n_rows=n_rows,
        )
