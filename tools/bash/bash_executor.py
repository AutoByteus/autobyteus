"""
This module provides the BashExecutor tool, a utility to execute bash commands asynchronously and retrieve their output.

Classes:
    BashExecutor: Tool for executing bash commands.
"""

import asyncio
import subprocess
import logging
from typing import Optional, TYPE_CHECKING, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.events.event_types import EventType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext


logger = logging.getLogger(__name__)


class BashExecutor(BaseTool):
    """
    A tool that allows for the execution of bash commands and retrieves their output.
    """

    def __init__(self):
        """
        Initialize the BashExecutor tool.
        """
        super().__init__()

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the BashExecutor tool.

        Returns:
            str: An XML description of how to use the BashExecutor tool.
        """
        return '''BashExecutor: Executes bash commands and retrieves their output. Usage:
    <command name="BashExecutor">
        <arg name="command">bash command</arg>
    </command>
    where "bash command" is a string containing the command to be executed.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> str:
        """
        Execute a bash command asynchronously and return its output.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Keyword arguments containing the bash command to be executed. 
                      The command should be specified as 'command'.

        Returns:
            str: The output of the executed command.

        Raises:
            ValueError: If the 'command' keyword argument is not specified.
            subprocess.CalledProcessError: If the command execution fails.
        """
        command: Optional[str] = kwargs.get('command')
        if not command:
            raise ValueError("The 'command' keyword argument must be specified.")

        logger.debug(f"Agent '{context.agent_id}' executing command: {command} via BashExecutor.")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_message = stderr.decode().strip()
                logger.error(f"Agent '{context.agent_id}' command failed with return code {process.returncode}: {error_message}")
                self.emit(EventType.TOOL_EXECUTION_FAILED, error_message) # Assuming EventType.TOOL_EXECUTION_FAILED is defined
                raise subprocess.CalledProcessError(
                    returncode=process.returncode,
                    cmd=command,
                    output=stdout.decode().strip(),
                    stderr=error_message
                )

            output = stdout.decode().strip()
            logger.debug(f"Agent '{context.agent_id}' command output: {output}")
            return output

        except Exception as e:
            logger.exception(f"Agent '{context.agent_id}' an error occurred while executing the command: {str(e)}")
            self.emit(EventType.TOOL_EXECUTION_FAILED, str(e))
            raise
