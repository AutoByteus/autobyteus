# autobyteus/source_code_tree/file_explorer/traversal_ignore_strategy/specific_folder_ignore_strategy.py

import os
from typing import List
import pathlib

from autobyteus.codeverse.core.file_explorer.traversal_ignore_strategy.traversal_ignore_strategy import TraversalIgnoreStrategy

class SpecificFolderIgnoreStrategy(TraversalIgnoreStrategy):
    """
    A strategy to ignore specific folders. The folders to ignore are given as relative paths from a root directory.
    """

    def __init__(self, root_path: str, folders_to_ignore: List[str]):
        """
        Initialize SpecificFolderIgnoreStrategy.

        Args:
            root_path (str): The root path of the workspace.
            folders_to_ignore (List[str]): A list of folders to ignore.
        """
        self.root_path = pathlib.Path(root_path)  # Store the root path as a Path object
        self.folders_to_ignore = folders_to_ignore

    def should_ignore(self, path: str) -> bool:
        """
        Determines if a folder should be ignored based on the relative path from the root path to the folder.

        Args:
            path (str): The path of the folder.

        Returns:
            bool: True if the folder should be ignored, False otherwise.
        """
        relative_path = str(pathlib.Path(path).relative_to(self.root_path))  # Compute the relative path
        if not relative_path:  # The path is for the root node
            relative_path = str(self.root_path)
        return relative_path in self.folders_to_ignore
