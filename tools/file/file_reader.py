# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/autobyteus/tools/file_reader.py
"""
This module provides the FileReader tool, a utility to read files.

Classes:
    FileReader: Tool for reading files.
"""

import os
import logging
from typing import TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class FileReader(BaseTool):
    """
    A tool that allows for reading files. If the specified file does not exist,
    it will raise a FileNotFoundError.
    """

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the FileReader tool.

        Returns:
            str: An XML description of how to use the FileReader tool.
        """
        return '''FileReader: Reads content from a specified file. Usage:
    <command name="FileReader">
    <arg name="path">file_path</arg>
    </command>
    where "file_path" is the path to the file to be read.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Read the content of the file at the specified path.

        Args:
            context: The AgentContext of the calling agent.
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

        logger.info(f"Agent '{context.agent_id}' attempting to read file: {path}")

        if not os.path.exists(path):
            logger.error(f"Agent '{context.agent_id}': File not found at {path}")
            raise FileNotFoundError(f"The file at {path} does not exist.")

        try:
            with open(path, 'r', encoding='utf-8') as file: # Specify encoding
                content = file.read()
            logger.info(f"Agent '{context.agent_id}': Successfully read file {path}. Content length: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"Agent '{context.agent_id}': Error reading file {path}: {e}", exc_info=True)
            raise # Re-raise the exception to be caught by BaseTool.execute
