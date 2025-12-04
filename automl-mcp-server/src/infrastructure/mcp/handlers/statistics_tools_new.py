"""
Statistics Tools Entry Point for MCP

This module serves as the main entry point for registering all statistics tools.
The actual tool implementations have been refactored into domain-specific modules
in the statistics/ directory.

Domain Modules:
    - statistics/eda_tools.py: EDA and Auto-Analysis (14 tools)
    - statistics/tableone_tools.py: Table 1 Generation (5 tools)
    - statistics/survival_tools.py: Survival Analysis (4 tools)
    - statistics/propensity_tools.py: Propensity Score Analysis (5 tools)
    - statistics/roc_tools.py: ROC/AUC Analysis (8 tools)
    - statistics/power_tools.py: Power Analysis (19 tools)
    - statistics/jobs_tools.py: Job Management (3 tools)

Total: 58 MCP Tools

Architecture:
    This refactoring follows DDD principles with Single Responsibility Principle.
    Each domain module is under 800 lines for maintainability.
"""
import logging

from mcp.server.fastmcp import FastMCP

from .statistics import register_all_statistics_tools

logger = logging.getLogger(__name__)


def register_statistics_tools(mcp: FastMCP, automl_client) -> None:
    """
    Register all statistics tools with MCP server.
    
    This is the main entry point called from the MCP server initialization.
    It delegates to the modular statistics package for actual tool registration.
    
    Args:
        mcp: FastMCP server instance
        automl_client: AutoML client for backend communication
    """
    logger.info("Registering statistics tools from modular package...")
    register_all_statistics_tools(mcp, automl_client)
    logger.info("Statistics tools registration complete")
