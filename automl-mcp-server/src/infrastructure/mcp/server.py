"""
AutoML MCP Server

A Model Context Protocol server providing AutoML capabilities for AI agents.

Architecture:
    This server wraps the AutoML REST API with MCP tools.
    - Tools are non-blocking (training runs in background)
    - Use get_job_status to poll for completion
    - Results available via get_model_leaderboard and predict

Usage:
    # Development mode with MCP inspector
    mcp dev src/infrastructure/mcp/server.py
    
    # Direct execution (stdio transport)
    python -m src.infrastructure.mcp.server
    
    # SSE transport for remote access
    python -m src.infrastructure.mcp.server --transport sse --port 8002

Workflow:
    1. Agent calls register_dataset(minio_path) → gets dataset_id
    2. Agent calls submit_automl_job(dataset_id, ...) → gets job_id (immediate return!)
    3. Agent tells user "Training started, I'll check progress..."
    4. Agent polls get_job_status(job_id) until status == "completed"
    5. Agent calls get_model_leaderboard(model_id) to show results
    6. Agent can now use predict(model_id, new_dataset_id) for inference
"""
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import default_config
from .handlers import AutoMLHandler

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AutoMLMcpServer:
    """
    Main MCP Server for AutoML.
    
    Orchestrates:
    - FastMCP server initialization
    - AutoML tool registration
    
    Design follows medical-calc-mcp patterns.
    """
    
    def __init__(self, config=None, host: str = "127.0.0.1", port: int = 8000):
        """Initialize the MCP server."""
        self._config = config or default_config
        
        # Create FastMCP server
        self._mcp = FastMCP(
            name=self._config.name,
            json_response=self._config.json_response,
            instructions=self._config.instructions,
            host=host,
            port=port,
        )
        
        # Initialize handlers
        self._init_handlers()
        
        logger.info(f"AutoML MCP Server initialized: {self._config.name}")

    def _init_handlers(self) -> None:
        """Initialize all MCP handlers"""
        self._automl_handler = AutoMLHandler(self._mcp)

    @property
    def mcp(self) -> FastMCP:
        """Get the FastMCP server instance"""
        return self._mcp

    def run(self, transport: str = "stdio") -> None:
        """
        Run the MCP server.
        
        Args:
            transport: Transport type ("stdio", "sse", or "streamable-http")
        """
        logger.info(f"Starting MCP server with transport: {transport}")
        
        if transport == "http":
            self._mcp.run(transport="streamable-http")
        elif transport == "sse":
            self._mcp.run(transport="sse")
        else:
            self._mcp.run()


# =============================================================================
# Module-level server instance
# =============================================================================

_server = None


def get_server(host: str = "127.0.0.1", port: int = 8000) -> AutoMLMcpServer:
    """Get or create the server instance"""
    global _server
    if _server is None:
        _server = AutoMLMcpServer(host=host, port=port)
    return _server


def _get_mcp():
    return get_server().mcp


class _McpProxy:
    def __getattr__(self, name):
        return getattr(get_server().mcp, name)


mcp = _McpProxy()


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the MCP server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoML MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport type"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8002,
        help="Port for SSE/HTTP transport"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for SSE/HTTP transport"
    )
    
    args = parser.parse_args()
    
    get_server(host=args.host, port=args.port).run(transport=args.transport)


if __name__ == "__main__":
    main()
