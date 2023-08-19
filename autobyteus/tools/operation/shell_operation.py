
"""
# tools/operation/shell_operation.py

This module contains the ShellOperation class used for executing and undoing shell commands.
"""

from tools.operation.operation import Operation
from tools.handlers.shell_handler import ShellHandler

class ShellOperation(Operation):
    def __init__(self, command: str, undo_command: str):
        """
        Initializes a ShellOperation instance.

        Args:
            command (str): The shell command to be executed.
            undo_command (str): The shell command to be executed to undo the operation.
        """
        self.command = command
        self.undo_command = undo_command
        self.shell_handler = ShellHandler()

    def execute(self):
        """
        Executes the shell command.

        Returns:
            str: The output after executing the shell command.
        """
        return self.shell_handler.handle_operation(self.command)

    def undo(self):
        """
        Executes the undo shell command.

        Returns:
            str: The output after executing the undo shell command.
        """
        return self.shell_handler.handle_operation(self.undo_command)

    def to_dict(self) -> dict:
        """
        Converts the ShellOperation object to a dictionary.

        Returns:
            dict: Dictionary representation of the ShellOperation object.
        """
        return {
            "command": self.command,
            "undo_command": self.undo_command
        }

    @staticmethod
    def from_dict(data: dict) -> 'ShellOperation':
        """
        Creates a ShellOperation instance from a dictionary.

        Args:
            data (dict): Dictionary containing shell operation data.

        Returns:
            ShellOperation: An instance of ShellOperation.
        """
        return ShellOperation(data['command'], data['undo_command'])
