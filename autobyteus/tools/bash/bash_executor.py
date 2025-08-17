import asyncio
import subprocess
import logging
import shutil
import tempfile
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool 
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="BashExecutor", category=ToolCategory.SYSTEM)
async def bash_executor(context: Optional['AgentContext'], command: str) -> str:
    """
    Executes bash commands using the '/bin/bash' interpreter.
    On success, it returns a formatted string containing the command's standard output (stdout) and/or diagnostic logs.
    On failure, it raises an exception.
    - If a command has only stdout, its content is returned directly.
    - If a command has diagnostic output (from stderr), it will be included and labeled as 'LOGS' in the output.
    'command' is the bash command string to be executed.
    The command is executed in the agent's workspace directory if available.
    """
    if not shutil.which("bash"):
        error_msg = "'bash' executable not found in system PATH. The BashExecutor tool cannot be used."
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

    logger.debug(f"Functional BashExecutor tool executing for '{agent_id_str}': {command} in cwd from {log_cwd_source}")

    try:
        # Explicitly use 'bash -c' for reliable execution
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
            error_message = stderr_output if stderr_output else "Unknown error"
            if not error_message and process.returncode != 0:
                error_message = f"Command failed with exit code {process.returncode} and no stderr output."
            
            logger.error(f"Command '{command}' failed with return code {process.returncode}: {error_message}")
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=command,
                output=stdout_output,
                stderr=error_message
            )
        
        # Adaptive return for successful commands to provide maximum context to the agent.
        if stdout_output and stderr_output:
            return f"STDOUT:\n{stdout_output}\n\nLOGS:\n{stderr_output}"
        elif stdout_output:
            return stdout_output  # Keep it simple for commands with only stdout
        elif stderr_output:
            return f"LOGS:\n{stderr_output}"
        else:
            return "Command executed successfully with no output."

    except subprocess.CalledProcessError:
        raise
    except FileNotFoundError:
        # This can be raised by create_subprocess_exec if 'bash' is not found, despite the initial check.
        logger.error("'bash' executable not found when attempting to execute command. Please ensure it is installed and in the PATH.")
        raise
    except Exception as e: 
        logger.exception(f"An error occurred while preparing or executing command '{command}': {str(e)}")
        raise RuntimeError(f"Failed to execute command '{command}': {str(e)}")
