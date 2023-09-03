# autobyteus/source_code_tree/file_explorer/directory_traversal.py

import os
import pathlib
from typing import List, Optional
from src.source_code_tree.file_explorer.traversal_ignore_strategy.traversal_ignore_strategy import TraversalIgnoreStrategy
from src.source_code_tree.file_explorer.tree_node import TreeNode
from src.source_code_tree.file_explorer.sort_strategy.default_sort_strategy import DefaultSortStrategy
from src.source_code_tree.file_explorer.sort_strategy.sort_strategy import SortStrategy


class DirectoryTraversal:
    """
    A class used to traverse directories and represent the directory structure as a TreeNode.
    The traversal order follows a specified SortStrategy.

    Methods
    -------
    build_tree(folder_path: str) -> TreeNode:
        Traverses a specified directory and returns its structure as a TreeNode.
    """

    def __init__(self, strategies: Optional[List[TraversalIgnoreStrategy]] = None, 
                 sort_strategy: Optional[SortStrategy] = None):
        """
        Initialize DirectoryTraversal.

        Args:
            strategies (Optional[List[TraversalIgnoreStrategy]]): A list of strategies to ignore files or folders.
                If none is provided, no file or folder will be ignored.
            sort_strategy (Optional[SortStrategy]): A strategy for sorting directories and files.
                If none is provided, DefaultSortStrategy is used.
        """
        self.strategies = strategies or []
        self.sort_strategy = sort_strategy or DefaultSortStrategy()

    def build_tree(self, folder_path: str) -> TreeNode:
        """
        Traverses a specified directory and returns its structure as a TreeNode.

        Parameters:
        ----------
        folder_path : str
            The path of the directory to be traversed.

        Returns:
        -------
        TreeNode
            The root node of the directory structure.
        """
        name = os.path.basename(folder_path)
        node = TreeNode(name, folder_path, os.path.isfile(folder_path))

        if not node.is_file:  # if the node is a directory, we add its children
            children_paths = os.listdir(folder_path)
            sorted_paths = self.sort_strategy.sort(paths=[os.path.abspath(os.path.join(folder_path, p)) for p in children_paths])
            
            for child_path in sorted_paths:
                full_child_path = os.path.join(folder_path, child_path)
                if any(strategy.should_ignore(full_child_path) for strategy in self.strategies):
                    continue

                child_node = self.build_tree(full_child_path)
                node.add_child(child_node)

        return node
