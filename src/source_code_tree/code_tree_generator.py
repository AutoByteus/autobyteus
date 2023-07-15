"""
source_code_tree_generator.py: A Python module that provides the SourceCodeTreeGenerator class.

The SourceCodeTreeGenerator class is responsible for generating a tree structure for a specified folder.
It uses the DirectoryTraversal and TreeFormatter classes to perform its tasks.

Features:
- Generate a tree structure from a given folder path.
- Format the tree structure for user-friendly display.

Usage:
- from source_code_tree_generator import SourceCodeTreeGenerator
- ctg = SourceCodeTreeGenerator(file_system_access)
- tree = ctg.generate_tree("path/to/folder")
- print(tree)
"""

from src.source_code_tree.directory_traversal import DirectoryTraversal
from src.source_code_tree.file_system_access import FileSystemAccess
from src.source_code_tree.tree_formatter import TreeFormatter


class SourceCodeTreeGenerator:
    # Constructor takes a FileSystemAccess instance as a dependency
    def __init__(self, file_system_access: FileSystemAccess):
        self.directory_traversal = DirectoryTraversal(file_system_access)
        self.tree_formatter = TreeFormatter()

    # Generate a tree structure for a specified folder
    def generate_tree(self, folder_path: str) -> str:
        tree_structure = self.directory_traversal.traverse(folder_path, level=0)
        formatted_tree = self.tree_formatter.format_tree(tree_structure)
        return formatted_tree
