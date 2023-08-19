import os
from tools.operation.operation import Operation

class FileRenameOperation(Operation):
    """Class to handle file renaming operations."""
    
    def __init__(self, source_path: str, destination_path: str):
        """
        Initializes a new instance of the FileRenameOperation class.
        
        Args:
        - source_path (str): The original path of the file to be renamed.
        - destination_path (str): The new path where the file should be renamed to.
        """
        self.source_path = source_path
        self.destination_path = destination_path

    def execute(self) -> None:
        """Renames the file from source_path to destination_path."""
        os.rename(self.source_path, self.destination_path)

    def undo(self) -> None:
        """Renames the file back from destination_path to source_path."""
        os.rename(self.destination_path, self.source_path)

    def to_dict(self) -> dict:
        """
        Serializes the operation details into a dictionary.
        
        Returns:
        - dict: A dictionary representation of the operation.
        """
        return {
            "type": "FileRenameOperation",
            "source_path": self.source_path,
            "destination_path": self.destination_path
        }

    @staticmethod
    def from_dict(data: dict) -> 'FileRenameOperation':
        """
        Deserializes the operation from dictionary data.
        
        Args:
        - data (dict): The dictionary containing operation details.
        
        Returns:
        - FileRenameOperation: An instance of the FileRenameOperation class.
        """
        return FileRenameOperation(data["source_path"], data["destination_path"])


