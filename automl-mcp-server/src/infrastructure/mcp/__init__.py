"""
MCP Server Implementation

Provides the FastMCP-based server for exposing AutoML capabilities
via the Model Context Protocol.
"""

from .config import McpServerConfig, default_config
from .server import AutoMLMcpServer, main, mcp

__all__ = [
    "mcp",
    "main",
    "AutoMLMcpServer",
    "McpServerConfig",
    "default_config",
]
