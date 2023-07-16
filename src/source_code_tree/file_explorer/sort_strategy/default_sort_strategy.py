# src/source_code_tree/file_explorer/sort_strategy/default_sort_strategy.py

import os
from typing import List, Tuple
from src.source_code_tree.file_explorer.sort_strategy.sort_strategy import SortStrategy


class DefaultSortStrategy(SortStrategy):
    """
    Default sorting strategy for directory traversal.

    The strategy is to sort folders and files so that all directories come first, 
    all files come later, and directories starting with a dot come before others.
    """

    def sort(self, paths: List[str]) -> List[str]:
        paths.sort(key=self._sort_key)
        return paths
    
    def _sort_key(self, path: str) -> tuple:
        """
        Returns a tuple that can be used for sorting paths.

        Parameters:
        ----------
        path : str
            The path to be sorted.

        Returns:
        -------
        tuple
            The sort key for the path.
        """
        is_directory = os.path.isdir(path)
        starts_with_dot = os.path.basename(path).startswith('.')
        return (not is_directory, starts_with_dot, path)
