"""
This module provides the FileWriter tool, a utility to write files.

Classes:
    FileWriter: Tool for writing files.
"""

import os
import logging
import asyncio # For asyncio.to_thread
from typing import TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class FileWriter(BaseTool):
    """
    A tool that allows for writing files. If the specified directory does not exist,
    it will create the necessary directories.
    """

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the FileWriter tool.

        Returns:
            str: An XML description of how to use the FileWriter tool.
        """
        return '''FileWriter: Creates a file with specified content. Usage:
    <command name="FileWriter">
    <arg name="path">file_path</arg>
    <arg name="content">file_content</arg>
    </command>
    where "file_path" is the path to create the file and "file_content" is the content to write to the file.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Write the content to a file at the specified path asynchronously.

        Args:
            context: The AgentContext of the calling agent.
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
        if content is None: # Content can be an empty string, but not None
            raise ValueError("The 'content' keyword argument must be specified.")
        if not isinstance(content, str): # Ensure content is a string
            logger.warning(f"FileWriter for agent '{context.agent_id}' received non-string content (type: {type(content)}). Converting to string.")
            content = str(content)


        logger.info(f"Agent '{context.agent_id}' attempting to write to file: {path}. Content length: {len(content)}")

        def write_file_sync():
            # Ensure the directory exists
            dir_name = os.path.dirname(path)
            if dir_name: # Check if dirname is not empty (e.g. for files in current dir)
                os.makedirs(dir_name, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as file: # Specify encoding
                file.write(content)

        try:
            await asyncio.to_thread(write_file_sync)
            success_message = f"File created/updated successfully at {path}"
            logger.info(f"Agent '{context.agent_id}': {success_message}")
            return success_message
        except Exception as e:
            logger.error(f"Agent '{context.agent_id}': Error writing file {path}: {e}", exc_info=True)
            raise # Re-raise to be caught by BaseTool.execute

