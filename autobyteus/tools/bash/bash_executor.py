"""
This module provides the BashExecutor tool, a utility to execute bash commands and retrieve their output.

Classes:
    BashExecutor: Tool for executing bash commands.
"""

import subprocess
import asyncio
from autobyteus.tools.base_tool import BaseTool

class BashExecutor(BaseTool):
    """
    A tool that allows for the execution of bash commands and retrieves their output.
    """

    def __init__(self):
        """
        Initialize the BashExecutor tool.
        """
        super().__init__()

    def tool_usage(self):
        """
        Return a string describing the usage of the BashExecutor tool.

        Returns:
            str: A description of how to use the BashExecutor tool.
        """
        return 'BashExecutor: Executes bash commands and retrieves their output. Usage: <<<BashExecutor(command="bash command")>>>, where "bash command" is a string containing the command to be executed.'

    def tool_usage_xml(self):
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

    def _execute(self, **kwargs):
        """
        Execute a bash command and return its output.

        Args:
            **kwargs: Keyword arguments containing the bash command to be executed. The command should be specified as 'command'.

        Returns:
            str: The output of the executed command.

        Raises:
            ValueError: If the 'command' keyword argument is not specified.
        """
        command = kwargs.get('command')
        if not command:
            raise ValueError("The 'command' keyword argument must be specified.")

        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.stdout.strip()

    async def execute_async(self, **kwargs):
        """
        Execute a bash command asynchronously and return its output.

        Args:
            **kwargs: Keyword arguments containing the bash command to be executed. The command should be specified as 'command'.

        Returns:
            str: The output of the executed command.

        Raises:
            ValueError: If the 'command' keyword argument is not specified.
        """
        command = kwargs.get('command')
        if not command:
            raise ValueError("The 'command' keyword argument must be specified.")

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        return stdout.decode().strip()