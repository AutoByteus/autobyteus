# autobyteus/source_code_tree/file_explorer/traversal_ignore_strategy.py

from abc import ABC, abstractmethod
import os
import fnmatch
import pathlib
from typing import List

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


class DotIgnoreStrategy(TraversalIgnoreStrategy):
    """
    A strategy to ignore files or folders starting with a dot.
    """

    def should_ignore(self, path: str) -> bool:
        return os.path.basename(path).startswith('.')


class SpecificFolderIgnoreStrategy(TraversalIgnoreStrategy):
    """
    A strategy to ignore specific folders.
    """

    def __init__(self, folders_to_ignore: List[str]):
        """
        Initialize SpecificFolderIgnoreStrategy.

        Args:
            folders_to_ignore (List[str]): A list of folders to ignore.
        """
        self.folders_to_ignore = folders_to_ignore

    def should_ignore(self, path: str) -> bool:
        return os.path.basename(path) in self.folders_to_ignore


class GitIgnoreStrategy(TraversalIgnoreStrategy):
    """
    A strategy to ignore files and folders specified in a .gitignore file.
    """

    def __init__(self, root_path: str):
        """
        Initialize GitIgnoreStrategy.

        Args:
            root_path (str): The root path of the workspace.
        """
        self.root_path = pathlib.Path(root_path)  # Store the root path as a Path object
        self.ignore_patterns = []
        gitignore_path = os.path.join(root_path, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as gitignore_file:
                self.ignore_patterns = gitignore_file.read().splitlines()

    def should_ignore(self, path: str) -> bool:
        """
        Determines if a file or folder should be ignored based on patterns specified in a .gitignore file.

        The method iterates over all the ignore patterns. For each pattern, if it's a directory pattern
        (ending with '/'), it removes the trailing slash and appends one to the path (if it's not already there)
        before performing the match. For file patterns, it performs the match directly.

        Args:
            path (str): The path of the file or folder.

        Returns:
            bool: True if the file or folder matches a pattern in the .gitignore file and should be ignored, 
                  False otherwise.
        """
        relative_path = pathlib.Path(path).relative_to(self.root_path)  # Compute the relative path
        for pattern in self.ignore_patterns:
            if pattern.endswith('/'):  # The pattern is for a directory
                if fnmatch.fnmatch(os.path.join(relative_path, ''), pattern):
                    return True
            else:  # The pattern is for a file
                if fnmatch.fnmatch(relative_path, pattern):
                    return True
        return False
