"""
This module provides the BashExecutor tool, a utility to execute bash commands and retrieve their output.

Classes:
    BashExecutor: Tool for executing bash commands.
"""

import subprocess
from autobyteus.tools.base_tool import BaseTool

class BashExecutor(BaseTool):
    """
    A tool that allows for the execution of bash commands and retrieves their output.
    """
    def execute(self, **kwargs):
        """
        Execute a bash command and return its output.

        Args:
            **kwargs: Keyword arguments containing the bash command to be executed. The command should be specified as 'command'.

        Returns:
            str: The output of the executed command.
        """
        command = kwargs.get('command')
        if not command:
            raise ValueError("The 'command' keyword argument must be specified.")

        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
