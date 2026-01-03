"""
stop_background_process tool - Stop background processes.

Terminates a background process started with start_background_process.
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


@tool(name="stop_background_process", category=ToolCategory.SYSTEM)
async def stop_background_process(
    context: Optional['AgentContext'],
    process_id: str
) -> dict:
    """
    Stop a background process.

    Terminates a process that was started with start_background_process.
    Sends SIGTERM first for graceful shutdown, then SIGKILL if the
    process doesn't terminate.

    Args:
        process_id: ID of the process to stop.

    Returns:
        dict with:
        - status: "stopped" if process was found and stopped,
                  "not_found" if process ID doesn't exist
        - process_id: The process identifier

    Examples:
        - Stop a dev server when done testing
        - Clean up processes before shutting down
    """
    manager = _get_background_manager(context)
    
    logger.info(f"Stopping background process: {process_id}")
    success = await manager.stop_process(process_id)
    
    return {
        "status": "stopped" if success else "not_found",
        "process_id": process_id
    }
