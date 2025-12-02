"""
AutoML MCP Server - Main Entry Point

Supports multiple transport modes:
- stdio: Local mode for MCP Inspector and Claude Desktop
- sse: Server-Sent Events for remote/Docker deployment

Usage:
    # Local STDIO mode (default)
    python src/main.py
    
    # SSE mode for remote access
    python src/main.py --mode sse --host 0.0.0.0 --port 8002
"""

import argparse
import os
import sys
import logging
from pathlib import Path

# Ensure the project root is in the path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the MCP server application"""
    from src.infrastructure.mcp.server import AutoMLMcpServer
    return AutoMLMcpServer()


def run_stdio():
    """Run in STDIO mode (local, for Claude Desktop)"""
    logger.info("Starting AutoML MCP Server in STDIO mode...")
    server = create_app()
    server.run(transport="stdio")


def run_sse(host: str = "0.0.0.0", port: int = 8002):
    """Run in SSE mode (remote, for Docker/cloud deployment)"""
    logger.info(f"Starting AutoML MCP Server in SSE mode on {host}:{port}...")
    os.environ["MCP_HOST"] = host
    os.environ["MCP_PORT"] = str(port)
    server = create_app()
    server.run(transport="sse")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="AutoML MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local mode (for VS Code Copilot / Claude Desktop)
  python src/main.py
  
  # Remote SSE mode (for Docker deployment)
  python src/main.py --mode sse --port 8002
  
  # Development with MCP Inspector
  mcp dev src/infrastructure/mcp/server.py
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_MODE", "stdio"),
        help="Transport mode (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host for SSE mode (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8002")),
        help="Port for SSE mode (default: 8002)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "stdio":
        run_stdio()
    elif args.mode == "sse":
        run_sse(args.host, args.port)


if __name__ == "__main__":
    main()
