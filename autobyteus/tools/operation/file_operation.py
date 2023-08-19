"""
File: tools/operation/file_operation.py
Module for managing file operations.
"""

from tools.operation.operation import Operation
import os

class FileOperation(Operation):
    """
    Represents a file operation (read, write, append).
    """

    def __init__(self, filepath: str, operation_type: str, data: str = None):
        """
        Initializes a FileOperation.
        
        :param filepath: Path to the file on which the operation is to be performed.
        :param operation_type: Type of operation (read, write, append).
        :param data: Data to be written or appended. Not required for read operation.
        """
        self.filepath = filepath
        self.operation_type = operation_type
        self.data = data
        self.backup_data = None

    def execute(self):
        """
        Executes the file operation.
        """
        if self.operation_type == "read":
            with open(self.filepath, 'r') as file:
                return file.read()
        elif self.operation_type in ["write", "append"]:
            # Backup current content for undo feature
            with open(self.filepath, 'r') as file:
                self.backup_data = file.read()

            mode = 'w' if self.operation_type == "write" else 'a'
            with open(self.filepath, mode) as file:
                file.write(self.data)
        else:
            raise ValueError("Invalid operation type.")

    def undo(self):
        """
        Reverts the file operation.
        """
        if self.operation_type in ["write", "append"] and self.backup_data is not None:
            with open(self.filepath, 'w') as file:
                file.write(self.backup_data)

    def to_dict(self) -> dict:
        """
        Serializes the FileOperation object into a dictionary.
        
        :return: Dictionary representation of the object.
        """
        return {
            "filepath": self.filepath,
            "operation_type": self.operation_type,
            "data": self.data
        }

    @staticmethod
    def from_dict(data: dict) -> 'FileOperation':
        """
        Deserializes the dictionary into a FileOperation object.
        
        :param data: Dictionary representation of the object.
        :return: FileOperation object.
        """
        return FileOperation(data["filepath"], data["operation_type"], data["data"])
