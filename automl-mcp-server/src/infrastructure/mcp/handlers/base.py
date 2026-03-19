"""
Base Handler for MCP Tools

Common utilities and base class for all handlers.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)


async def wait_for_completion(
    check_status: Callable[[], Awaitable[Dict[str, Any]]],
    terminal_states: Optional[list[str]] = None,
    poll_interval: int = 10,
    timeout: int = 3600,
    ctx=None,
) -> Dict[str, Any]:
    """
    Generic polling helper for waiting on async operations.

    Args:
        check_status: Async function that returns status dict with 'status' key
        terminal_states: List of status values that indicate completion
        poll_interval: Seconds between polls
        timeout: Maximum seconds to wait (0 = no timeout)
        ctx: Optional MCP Context for sending progress notifications to client

    Returns:
        Final status dict with elapsed_seconds added
    """
    if terminal_states is None:
        terminal_states = ["completed", "failed", "cancelled"]

    start_time = time.time()

    while True:
        status = await check_status()
        elapsed = time.time() - start_time

        # Report progress to MCP client via SSE
        if ctx is not None:
            progress = status.get("progress", 0)
            message = status.get("message") or status.get("status_message") or status.get("status", "")
            try:
                await ctx.report_progress(
                    progress=progress * 100,
                    total=100,
                    message=message,
                )
            except Exception as e:
                logger.debug(f"Failed to report progress: {e}")

        # Check if reached terminal state
        if status.get("status") in terminal_states:
            status["elapsed_seconds"] = round(elapsed, 1)
            return status

        # Check timeout
        if timeout > 0 and elapsed >= timeout:
            return {
                "status": "timeout",
                "status_message": f"Did not complete within {timeout} seconds",
                "last_status": status.get("status"),
                "last_progress": status.get("progress", 0),
                "elapsed_seconds": round(elapsed, 1),
            }

        await asyncio.sleep(poll_interval)
