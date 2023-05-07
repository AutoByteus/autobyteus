"""
directory_traversal.py: A Python module that provides the DirectoryTraversal class.

The DirectoryTraversal class is responsible for recursively traversing a folder and its subfolders,
building the tree structure as it goes. It interacts with the file system through an abstract
FileSystemAccess class.

Features:
- Traverse a folder and its subfolders to build a tree structure.

Usage:
- from source_code_tree.directory_traversal import DirectoryTraversal
- dt = DirectoryTraversal(file_system_access)
- tree_structure = dt.traverse("path/to/folder", level=0)
"""

from src.source_code_tree.file_system_access import FileSystemAccess


class DirectoryTraversal:
    def __init__(self, file_system_access: FileSystemAccess):
        self.file_system_access = file_system_access

    def traverse(self, folder_path, level):
        tree_structure = []

        for item in self.file_system_access.get_folder_items(folder_path):
            if self.file_system_access.is_folder(item):
                tree_structure.append((item, level, True))
                tree_structure.extend(self.traverse(item, level + 1))
            else:
                tree_structure.append((item, level, False))

        return tree_structure
