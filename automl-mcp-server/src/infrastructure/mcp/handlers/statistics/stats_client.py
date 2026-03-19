"""
Stats Client Singleton

Provides a singleton instance of StatsClient for use across statistics tools.
"""

from typing import Optional

# Re-export StatsClient from the original module
from ..stats_client import StatsClient

_stats_client: Optional[StatsClient] = None


def get_stats_client() -> StatsClient:
    """
    Get or create the singleton StatsClient instance.

    Returns:
        StatsClient instance
    """
    global _stats_client
    if _stats_client is None:
        _stats_client = StatsClient()
    return _stats_client


def reset_stats_client() -> None:
    """Reset the singleton instance (for testing)"""
    global _stats_client
    _stats_client = None
