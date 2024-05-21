"""
This module provides the FileGenerator tool, a utility to create files and directories.

Classes:
    FileGenerator: Tool for generating files and directories as needed.
"""

import os
from autobyteus.tools.base_tool import BaseTool

class FileGenerator(BaseTool):
    """
    A tool that allows for the creation of files. If the specified directory does not exist,
    it will be created.
    """
    def execute(self, **kwargs):
        """
        Create a file with the given content at the specified path.

        Args:
            **kwargs: Keyword arguments containing the path and content for file creation. The path should be specified as 'path', and the content should be specified as 'content'.

        Returns:
            str: A message indicating the file creation status.
        """
        path = kwargs.get('path')
        content = kwargs.get('content', '')

        if not path:
            raise ValueError("The 'path' keyword argument must be specified.")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as file:
            file.write(content)
        return f'File created at {path}'








