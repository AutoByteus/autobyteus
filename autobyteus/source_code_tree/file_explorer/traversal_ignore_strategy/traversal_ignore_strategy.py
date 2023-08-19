# src/source_code_tree/file_explorer/traversal_ignore_strategy/traversal_ignore_strategy.py

from abc import ABC, abstractmethod

class TraversalIgnoreStrategy(ABC):
    """
    Abstract class to provide a strategy for ignoring files or folders during directory traversal.
    """

    @abstractmethod
    def should_ignore(self, path: str) -> bool:
        """
        Determines whether a file or folder should be ignored during directory traversal.

        Args:
            path (str): The path of the file or folder.

        Returns:
            bool: True if the file or folder should be ignored, False otherwise.
        """
        pass
