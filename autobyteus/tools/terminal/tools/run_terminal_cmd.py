"""
run_terminal_cmd tool - Execute commands in a stateful terminal.

This tool replaces the stateless bash_executor with a PTY-based
implementation that maintains shell state (cd, environment variables).
"""

import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.tools.terminal.types import TerminalResult

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


def _get_terminal_manager(context: Optional['AgentContext']):
    """Get or create the terminal session manager for this agent.
    
    Args:
        context: The agent context.
        
    Returns:
        TerminalSessionManager instance.
    """
    from autobyteus.tools.terminal.terminal_session_manager import TerminalSessionManager
    
    if context is None:
        # Fallback for non-agent use
        if not hasattr(_get_terminal_manager, '_default_manager'):
            _get_terminal_manager._default_manager = TerminalSessionManager()
        return _get_terminal_manager._default_manager
    
    # Store manager in context for per-agent isolation
    if not hasattr(context, '_terminal_session_manager'):
        context._terminal_session_manager = TerminalSessionManager()
    
    return context._terminal_session_manager


def _get_cwd(context: Optional['AgentContext']) -> str:
    """Get the working directory for the terminal.
    
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


@tool(name="run_terminal_cmd", category=ToolCategory.SYSTEM)
async def run_terminal_cmd(
    context: Optional['AgentContext'],
    command: str,
    timeout_seconds: int = 30
) -> TerminalResult:
    """
    Execute a command in the terminal and wait for completion.

    The terminal maintains state between calls: directory changes (cd),
    environment variables (export), and shell state persist.

    This is like typing a command in a real terminal - each command
    runs in the same shell session.

    Args:
        command: The bash command to execute.
        timeout_seconds: Maximum time to wait for completion (default 30s).
                        Command is killed if timeout is exceeded.

    Returns:
        TerminalResult with:
        - stdout: Output from the command
        - stderr: Error output (may be mixed with stdout in PTY)
        - exit_code: Exit code if available
        - timed_out: True if command exceeded timeout
    
    Examples:
        - run_terminal_cmd("ls -la")
        - run_terminal_cmd("cd src && npm install", timeout_seconds=120)
        - run_terminal_cmd("export PATH=$PATH:/custom/bin")
    """
    manager = _get_terminal_manager(context)
    cwd = _get_cwd(context)
    
    # Ensure session is started
    await manager.ensure_started(cwd)
    
    logger.debug(f"Executing terminal command: {command}")
    result = await manager.execute_command(command, timeout_seconds)
    
    if result.timed_out:
        logger.warning(f"Command timed out: {command}")
    
    return result
