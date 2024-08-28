# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/autobyteus/tools/file_reader.py
"""
This module provides the FileReader tool, a utility to read files.

Classes:
    FileReader: Tool for reading files.
"""

import os
from autobyteus.tools.base_tool import BaseTool

class FileReader(BaseTool):
    """
    A tool that allows for reading files. If the specified file does not exist,
    it will raise a FileNotFoundError.
    """

    def tool_usage(self):
        """
        Return a string describing the usage of the FileReader tool.
        """
        return 'FileReader: Reads content from a specified file. Usage: <<<FileReader(path="file_path")>>>, where "file_path" is the path to the file to be read.'

    def tool_usage_xml(self):
        """
        Return an XML string describing the usage of the FileReader tool.
        """
        return '''FileReader: Reads content from a specified file. Usage:
    <command name="FileReader">
    <arg name="path">file_path</arg>
    </command>
    where "file_path" is the path to the file to be read.
    '''

    async def _execute(self, **kwargs):
        """
        Read the content of the file at the specified path.

        Args:
            **kwargs: Keyword arguments containing the path of the file to be read. 
                      The path should be specified as 'path'.

        Returns:
            str: The content of the file.

        Raises:
            ValueError: If the 'path' keyword argument is not specified.
            FileNotFoundError: If the specified file does not exist.
        """
        path = kwargs.get('path')

        if not path:
            raise ValueError("The 'path' keyword argument must be specified.")

        if not os.path.exists(path):
            raise FileNotFoundError(f"The file at {path} does not exist.")

        with open(path, 'r') as file:
            content = file.read()
        return content