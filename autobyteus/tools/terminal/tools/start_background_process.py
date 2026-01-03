"""
start_background_process tool - Start long-running processes.

Starts processes like servers (yarn dev, uvicorn) in the background
and returns immediately with a process ID for later reference.
"""

import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


def _get_background_manager(context: Optional['AgentContext']):
    """Get or create the background process manager for this agent.
    
    Args:
        context: The agent context.
        
    Returns:
        BackgroundProcessManager instance.
    """
    from autobyteus.tools.terminal.background_process_manager import BackgroundProcessManager
    
    if context is None:
        if not hasattr(_get_background_manager, '_default_manager'):
            _get_background_manager._default_manager = BackgroundProcessManager()
        return _get_background_manager._default_manager
    
    if not hasattr(context, '_background_process_manager'):
        context._background_process_manager = BackgroundProcessManager()
    
    return context._background_process_manager


def _get_cwd(context: Optional['AgentContext']) -> str:
    """Get the working directory for the process.
    
    Args:
        context: The agent context.
        
    Returns:
        Working directory path.
    """
    import tempfile
    
    if context and hasattr(context, 'workspace') and context.workspace:
        try:
            base_path = context.workspace.get_base_path()
            if base_path and isinstance(base_path, str):
                return base_path
        except Exception:
            pass
    
    return tempfile.gettempdir()


@tool(name="start_background_process", category=ToolCategory.SYSTEM)
async def start_background_process(
    context: Optional['AgentContext'],
    command: str
) -> dict:
    """
    Start a long-running process in the background.

    Use this for servers, watchers, or any process that doesn't
    terminate immediately. The process runs independently and
    you can check its output or stop it later using the returned
    process_id.

    Args:
        command: The command to run in background.
                Examples: "yarn dev", "uvicorn main:app", "npm start"

    Returns:
        dict with:
        - process_id: ID to reference this process later
        - status: "started"

    Examples:
        - start_background_process("yarn dev")
        - start_background_process("uvicorn app:main --reload")
        - start_background_process("python -m http.server 8000")
    
    After starting, use:
        - get_process_output(process_id) to check output
        - stop_background_process(process_id) to stop it
    """
    manager = _get_background_manager(context)
    cwd = _get_cwd(context)
    
    logger.info(f"Starting background process: {command}")
    process_id = await manager.start_process(command, cwd)
    
    return {
        "process_id": process_id,
        "status": "started"
    }
