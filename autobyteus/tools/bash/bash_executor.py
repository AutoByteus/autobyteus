import asyncio
import subprocess
import logging
from typing import TYPE_CHECKING

from autobyteus.tools import tool 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="BashExecutor") # Decorator infers name from function if not provided, but explicit is fine.
async def bash_executor(context: 'AgentContext', command: str) -> str: # Function name can be same as registered tool name
    """
    Executes bash commands and retrieves their standard output.
    'command' is the bash command string to be executed.
    Errors during command execution are raised as exceptions.
    """
    logger.debug(f"Functional BashExecutor tool executing for agent {context.agent_id if context else 'Unknown'}: {command}")

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode().strip() if stderr else "Unknown error"
            if not error_message and process.returncode != 0:
                error_message = f"Command failed with exit code {process.returncode} and no stderr output."
            
            logger.error(f"Command '{command}' failed with return code {process.returncode}: {error_message}")
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=command,
                output=stdout.decode().strip() if stdout else "",
                stderr=error_message
            )

        output = stdout.decode().strip() if stdout else ""
        logger.debug(f"Command '{command}' output: {output}")
        return output

    except subprocess.CalledProcessError:
        raise
    except Exception as e: 
        logger.exception(f"An error occurred while preparing or executing command '{command}': {str(e)}")
        raise RuntimeError(f"Failed to execute command '{command}': {str(e)}")
