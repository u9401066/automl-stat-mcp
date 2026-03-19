"""
Statistics Tools Base Module

Provides:
- Shared utilities and error handling
- StatsClient initialization
- Tool registration orchestration
"""

import logging
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


class StatsToolError(Exception):
    """Base exception for statistics tools"""

    pass


class StatsClientNotAvailable(StatsToolError):
    """Raised when stats client is not available"""

    pass


class DataNotFound(StatsToolError):
    """Raised when requested data is not found"""

    pass


def create_error_response(error: Exception, context: str = "") -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "status": "error",
        "error": str(error),
        "context": context,
    }


def create_success_response(data: Any, message: str = "") -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "status": "success",
        "data": data,
        "message": message,
    }


def register_all_statistics_tools(mcp: FastMCP, automl_client) -> None:
    """
    Register all statistics tools with MCP server.

    This function orchestrates the registration of all statistics tools
    organized by domain.
    """
    from .stats_client import get_stats_client

    stats_client = get_stats_client()

    # Import and register each domain's tools
    from .eda_tools import register_eda_tools
    from .jobs_tools import register_jobs_tools
    from .power import register_power_tools
    from .propensity_tools import register_propensity_tools
    from .roc_tools import register_roc_tools
    from .survival_tools import register_survival_tools
    from .tableone_tools import register_tableone_tools

    # Register in order
    register_eda_tools(mcp, stats_client)
    register_tableone_tools(mcp, stats_client)
    register_survival_tools(mcp, stats_client)
    register_propensity_tools(mcp, stats_client)
    register_roc_tools(mcp, stats_client)
    register_jobs_tools(mcp, stats_client)
    register_power_tools(mcp, stats_client)

    logger.info("Registered all statistics tools (58 tools across 7 domains)")
