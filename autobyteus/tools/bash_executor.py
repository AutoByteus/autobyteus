"""
This module provides the BashExecutor tool, a utility to execute bash commands and retrieve their output.

Classes:
    BashExecutor: Tool for executing bash commands.
"""

import subprocess
from src.tools.base_tool import BaseTool

class BashExecutor(BaseTool):
    """
    A tool that allows for the execution of bash commands and retrieves their output.
    """
    def execute(self, command):
        """
        Execute a bash command and return its output.
        
        Parameters:
            command (str): The bash command to be executed.
        
        Returns:
            str: The output of the executed command.
        """
        result = subprocess.run(command, capture_output=True, text=True, shell=True)
        return result.stdout.strip()