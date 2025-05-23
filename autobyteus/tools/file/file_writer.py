import os
import logging
from typing import TYPE_CHECKING

from autobyteus.tools import tool

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="FileWriter")
async def file_writer(context: 'AgentContext', path: str, content: str) -> str:
    """
    Creates or overwrites a file with specified content.
    'path' is the path where the file will be written.
    'content' is the string content to write.
    Creates parent directories if they don't exist.
    Raises IOError if file writing fails.
    """
    logger.debug(f"Functional FileWriter tool for agent {context.agent_id}, path: {path}")
    try:
        dir_path = os.path.dirname(path)
        if dir_path: # Only if path includes a directory part
            os.makedirs(dir_path, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(content)
        return f"File created/updated at {path}"
    except Exception as e:
        logger.error(f"Error writing file {path} for agent {context.agent_id}: {e}", exc_info=True)
        raise IOError(f"Could not write file at {path}: {str(e)}")
