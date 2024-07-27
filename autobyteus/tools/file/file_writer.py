"""
This module provides the FileWriter tool, a utility to write files.

Classes:
    FileWriter: Tool for writing files.
"""

import os
from autobyteus.tools.base_tool import BaseTool

class FileWriter(BaseTool):
    """
    A tool that allows for writing files. If the specified directory does not exist,
    it will create the necessary directories.
    """

    def tool_usage(self):
        """
        Return a string describing the usage of the FileWriter tool.
        """
        return 'FileWriter: Creates a file with specified content. Usage: <<<FileWriter(path="file_path", content="file_content")>>>, where "file_path" is the path to create the file and "file_content" is the content to write to the file.'

    def tool_usage_xml(self):
        """
        Return an XML string describing the usage of the FileWriter tool.
        """
        return '''FileWriter: Creates a file with specified content. Usage:
    <command name="FileWriter">
    <arg name="path">file_path</arg>
    <arg name="content">file_content</arg>
    </command>
    where "file_path" is the path to create the file and "file_content" is the content to write to the file.
    '''

    def _execute(self, **kwargs):
        """
        Write the content to a file at the specified path.

        Args:
            **kwargs: Keyword arguments containing the path of the file to be written
                      and the content to be written.
                      The path should be specified as 'path'.
                      The content should be specified as 'content'.

        Returns:
            str: A message indicating the file was created successfully.

        Raises:
            ValueError: If the 'path' or 'content' keyword argument is not specified.
        """
        path = kwargs.get('path')
        content = kwargs.get('content')

        if not path:
            raise ValueError("The 'path' keyword argument must be specified.")
        if content is None:
            raise ValueError("The 'content' keyword argument must be specified.")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as file:
            file.write(content)

        return f"File created at {path}"