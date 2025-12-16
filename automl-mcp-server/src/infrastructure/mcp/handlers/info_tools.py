"""
Info/Discovery Tools for MCP

Tools for discovering available algorithms and health checking.
"""
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..client import AutoMLClient


def register_info_tools(mcp: FastMCP, client: AutoMLClient) -> None:
    """Register info and discovery tools"""

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def list_algorithms() -> Dict[str, Any]:
        """
        List all available machine learning algorithms.

        Returns the algorithm codes (e.g., 'XGB', 'GBM') that can be used
        in training requests.

        Returns:
            algorithms: Dict mapping code to full name
            description: Usage instructions
        """
        return await client.list_algorithms()

    # @mcp.tool()  # HIDDEN: replaced by integrated tool
    async def health_check() -> Dict[str, Any]:
        """
        Check if the AutoML service is healthy.

        Returns:
            status: "healthy" if service is running
            version: Service version
        """
        return await client.health_check()
