# src/source_code_tree/file_explorer/directory_traversal.py

import os
from typing import List, Optional
import pathlib
from src.source_code_tree.file_explorer.traversal_ignore_strategy.traversal_ignore_strategy import TraversalIgnoreStrategy

from src.source_code_tree.file_explorer.tree_node import TreeNode

class DirectoryTraversal:
    """
    A class used to traverse directories and represent the directory structure as a TreeNode.

    Methods
    -------
    build_tree(folder_path: str) -> TreeNode:
        Traverses a specified directory and returns its structure as a TreeNode.
    """

    def __init__(self, strategies: Optional[List[TraversalIgnoreStrategy]] = None):
        """
        Initialize DirectoryTraversal.

        Args:
            strategies (Optional[List[TraversalIgnoreStrategy]]): A list of strategies to ignore files or folders.
                If none is provided, no file or folder will be ignored.
        """
        self.strategies = strategies or []

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
            for child_path in os.listdir(folder_path):
                full_child_path = os.path.join(folder_path, child_path)
                if any(strategy.should_ignore(full_child_path) for strategy in self.strategies):
                    continue

                child_node = self.build_tree(full_child_path)
                node.add_child(child_node)

        return node
