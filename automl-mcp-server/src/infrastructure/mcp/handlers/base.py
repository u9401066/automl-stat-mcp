"""
Base Handler for MCP Tools

Common utilities and base class for all handlers.
"""
import asyncio
from typing import Any, Dict, Callable
import time


async def wait_for_completion(
    check_status: Callable[[], Dict[str, Any]],
    terminal_states: list = ["completed", "failed", "cancelled"],
    poll_interval: int = 10,
    timeout: int = 3600,
) -> Dict[str, Any]:
    """
    Generic polling helper for waiting on async operations.
    
    Args:
        check_status: Async function that returns status dict with 'status' key
        terminal_states: List of status values that indicate completion
        poll_interval: Seconds between polls
        timeout: Maximum seconds to wait (0 = no timeout)
    
    Returns:
        Final status dict with elapsed_seconds added
    """
    start_time = time.time()
    
    while True:
        status = await check_status()
        elapsed = time.time() - start_time
        
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
