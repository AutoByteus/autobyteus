"""
File: tools/handlers/shell_handler.py
This module provides functionality to execute shell operations.
"""

import subprocess
import logging

class ShellHandler:
    """Handler to execute shell operations."""

    @staticmethod
    def handle_operation(operation) -> str:
        """Execute the given ShellOperation.

        Args:
            operation (ShellOperation): The shell operation to be executed.

        Returns:
            str: The output of the shell command.

        Raises:
            subprocess.CalledProcessError: If the shell command fails.
        """
        try:
            # Execute the shell command
            output = subprocess.check_output(operation.command, shell=True, stderr=subprocess.STDOUT)
            logging.info(f"Successfully executed shell command: {operation.command}")
            return output.decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to execute shell command: {operation.command}. Error: {e.output.decode('utf-8').strip()}")
            raise
