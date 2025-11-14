import asyncio
import subprocess
import logging
import shutil
import tempfile
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory
from .types import BashExecutionResult

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="execute_bash", category=ToolCategory.SYSTEM)
async def bash_executor(context: Optional['AgentContext'], command: str) -> BashExecutionResult:
    """
    Executes bash commands using the '/bin/bash' interpreter and returns a structured result.
    This tool does NOT raise an exception for failed commands. Instead, it captures the
    exit code, stdout, and stderr and returns them in a BashExecutionResult object.

    It is the responsibility of the agent to interpret the result.
    - An 'exit_code' of 0 typically indicates success.
    - A non-zero 'exit_code' indicates an error.
    - 'stdout' contains the standard output of the command.
    - 'stderr' contains the standard error output, which may include warnings or error messages.

    'command' is the bash command string to be executed.
    The command is executed in the agent's workspace directory if available.
    """
    if not shutil.which("bash"):
        error_msg = "'bash' executable not found in system PATH. The execute_bash tool cannot be used."
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
        
    agent_id_str = context.agent_id if context else "Non-Agent"
    
    effective_cwd = None
    log_cwd_source = ""

    if context and hasattr(context, 'workspace') and context.workspace:
        try:
            base_path = context.workspace.get_base_path()
            if base_path and isinstance(base_path, str):
                effective_cwd = base_path
                log_cwd_source = f"agent workspace: {effective_cwd}"
            else:
                logger.warning(f"Agent '{agent_id_str}' has a workspace, but it provided an invalid base path ('{base_path}'). "
                               f"Falling back to system temporary directory.")
        except Exception as e:
            logger.warning(f"Could not retrieve workspace for agent '{agent_id_str}': {e}. "
                           f"Falling back to system temporary directory.")

    if not effective_cwd:
        effective_cwd = tempfile.gettempdir()
        log_cwd_source = f"system temporary directory: {effective_cwd}"

    logger.debug(f"Functional execute_bash tool executing for '{agent_id_str}': {command} in cwd from {log_cwd_source}")

    try:
        process = await asyncio.create_subprocess_exec(
            'bash', '-c', command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=effective_cwd
        )
        stdout, stderr = await process.communicate()
        
        stdout_output = stdout.decode().strip() if stdout else ""
        stderr_output = stderr.decode().strip() if stderr else ""

        if process.returncode != 0:
            logger.warning(
                f"Command '{command}' completed with non-zero exit code {process.returncode}. "
                f"Stderr: {stderr_output}"
            )
        
        return BashExecutionResult(
            exit_code=process.returncode,
            stdout=stdout_output,
            stderr=stderr_output,
        )

    except FileNotFoundError:
        logger.error("'bash' executable not found when attempting to execute command. Please ensure it is installed and in the PATH.")
        raise
    except Exception as e: 
        logger.exception(f"An unexpected error occurred while preparing or executing command '{command}': {str(e)}")
        # For fundamental errors (not command failures), we still raise
        raise RuntimeError(f"Failed to execute command '{command}': {str(e)}")
