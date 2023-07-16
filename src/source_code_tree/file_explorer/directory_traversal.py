import os
from typing import Optional

from src.source_code_tree.file_explorer.tree_node import TreeNode

class DirectoryTraversal:
    """
    A class used to traverse directories and represent the directory structure as a TreeNode.

    Methods
    -------
    build_tree(folder_path: str) -> TreeNode:
        Traverses a specified directory and returns its structure as a TreeNode.
    """

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
                child_node = self.build_tree(os.path.join(folder_path, child_path))
                node.add_child(child_node)

        return node
