"""
get_process_output tool - Read output from background processes.

Returns recent output from a background process started with
start_background_process.
"""

import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


def _get_background_manager(context: Optional['AgentContext']):
    """Get the background process manager for this agent."""
    from autobyteus.tools.terminal.background_process_manager import BackgroundProcessManager
    
    if context is None:
        if not hasattr(_get_background_manager, '_default_manager'):
            _get_background_manager._default_manager = BackgroundProcessManager()
        return _get_background_manager._default_manager
    
    if not hasattr(context, '_background_process_manager'):
        context._background_process_manager = BackgroundProcessManager()
    
    return context._background_process_manager


@tool(name="get_process_output", category=ToolCategory.SYSTEM)
async def get_process_output(
    context: Optional['AgentContext'],
    process_id: str,
    lines: int = 100
) -> dict:
    """
    Get recent output from a background process.

    Use this to check what a background process (started with
    start_background_process) is outputting. This is useful to:
    - Verify a server started successfully
    - Check for errors in the output
    - Monitor progress of a long-running task

    Args:
        process_id: ID returned by start_background_process.
        lines: Number of recent lines to return (default 100).

    Returns:
        dict with:
        - output: Recent output lines from the process
        - is_running: True if process is still running
        - process_id: The process identifier

    Examples:
        - After starting "yarn dev", check output to verify server is ready
        - Check for compilation errors in build output
        - Monitor test runner output
    """
    manager = _get_background_manager(context)
    
    try:
        result = manager.get_output(process_id, lines)
        return {
            "output": result.output,
            "is_running": result.is_running,
            "process_id": result.process_id
        }
    except KeyError:
        logger.warning(f"Process not found: {process_id}")
        return {
            "output": "",
            "is_running": False,
            "process_id": process_id,
            "error": f"Process '{process_id}' not found. It may have already stopped or never existed."
        }
