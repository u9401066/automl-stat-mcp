"""
MCP Server Implementation

Provides the FastMCP-based server for exposing AutoML capabilities
via the Model Context Protocol.
"""

from .server import mcp, main, AutoMLMcpServer
from .config import McpServerConfig, default_config

__all__ = [
    "mcp",
    "main",
    "AutoMLMcpServer",
    "McpServerConfig",
    "default_config",
]
