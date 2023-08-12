"""
This module provides the FileGenerator tool, a utility to create files and directories.

Classes:
    FileGenerator: Tool for generating files and directories as needed.
"""

import os
from src.tools.base_tool import BaseTool

class FileGenerator(BaseTool):
    """
    A tool that allows for the creation of files. If the specified directory does not exist,
    it will be created.
    """
    def execute(self, path, content=''):
        """
        Create a file with the given content at the specified path.
        
        Parameters:
            path (str): The path where the file should be created.
            content (str): The content to write to the file. Default is an empty string.
        
        Returns:
            str: A message indicating the file creation status.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as file:
            file.write(content)
        return f'File created at {path}'
    









