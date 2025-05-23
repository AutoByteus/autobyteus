import os
import logging
from typing import TYPE_CHECKING

from autobyteus.tools import tool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="FileReader") # Keep registered name "FileReader"
async def file_reader(context: 'AgentContext', path: str) -> str: # function name can be same
    """
    Reads content from a specified file.
    'path' is the absolute or relative path to the file.
    Raises FileNotFoundError if the file does not exist.
    Raises IOError if file reading fails for other reasons.
    """
    logger.debug(f"Functional FileReader tool for agent {context.agent_id}, path: {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"The file at {path} does not exist.")
    try:
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        logger.error(f"Error reading file {path} for agent {context.agent_id}: {e}", exc_info=True)
        raise IOError(f"Could not read file at {path}: {str(e)}")
