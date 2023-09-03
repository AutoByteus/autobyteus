# autobyteus/source_code_tree/file_explorer/sort_strategy/default_sort_strategy.py

import os
from typing import List
from src.source_code_tree.file_explorer.sort_strategy.sort_strategy import SortStrategy


class DefaultSortStrategy(SortStrategy):
    """
    Default sorting strategy for directory traversal.

    The strategy is to sort folders and files such that all directories come first, 
    and all files come later. Both directories and files are sorted in alphabetical 
    order by their basename.
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
        return (not is_directory, os.path.basename(path))
