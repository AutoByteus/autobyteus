"""
file_system_access.py: A Python module that provides the FileSystemAccess abstract class
and its concrete implementations for Mac and Linux platforms.

The FileSystemAccess class defines an interface for interacting with the file system.
Concrete implementations of this interface should be provided for different platforms
or file system types.

Features:
- Abstract interface for file system access.
- Concrete implementations for Mac and Linux platforms.

Usage:
- Create a concrete implementation of the FileSystemAccess class for the desired platform.
- Inject the concrete implementation into the DirectoryTraversal class.
"""

from abc import ABC, abstractmethod
import os
from typing import List


class FileSystemAccess(ABC):
    @abstractmethod
    def get_folder_items(self, folder_path: str) -> List[str]:
        pass

    @abstractmethod
    def is_folder(self, item_path: str) -> bool:
        pass


class MacFileSystemAccess(FileSystemAccess):
    def get_folder_items(self, folder_path: str) -> List[str]:
        # Implement platform-specific functionality for Mac
        return os.listdir(folder_path)

    def is_folder(self, item_path: str) -> bool:
        return os.path.isdir(item_path)


class LinuxFileSystemAccess(FileSystemAccess):
    def get_folder_items(self, folder_path: str) -> List[str]:
        # Implement platform-specific functionality for Linux
        return os.listdir(folder_path)

    def is_folder(self, item_path: str) -> bool:
        return os.path.isdir(item_path)
