import os
import logging
from typing import TYPE_CHECKING

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="FileWriter", category=ToolCategory.FILE_SYSTEM)
async def file_writer(context: 'AgentContext', path: str, content: str) -> str:
    """
    Creates or overwrites a file with specified content.
    'path' is the path where the file will be written. If relative, it must be resolved against a configured agent workspace.
    'content' is the string content to write.
    Creates parent directories if they don't exist.
    Raises ValueError if a relative path is given without a valid workspace.
    Raises IOError if file writing fails.
    """
    logger.debug(f"Functional FileWriter tool for agent {context.agent_id}, initial path: {path}")
    
    final_path: str
    if os.path.isabs(path):
        final_path = path
        logger.debug(f"Path '{path}' is absolute. Using it directly.")
    else:
        if not context.workspace:
            error_msg = f"Relative path '{path}' provided, but no workspace is configured for agent '{context.agent_id}'. A workspace is required to resolve relative paths."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        base_path = context.workspace.get_base_path()
        if not base_path or not isinstance(base_path, str):
            error_msg = f"Agent '{context.agent_id}' has a configured workspace, but it provided an invalid base path ('{base_path}'). Cannot resolve relative path '{path}'."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        final_path = os.path.join(base_path, path)
        logger.debug(f"Path '{path}' is relative. Resolved to '{final_path}' using workspace base path '{base_path}'.")

    try:
        # It's good practice to normalize the path to handle things like '..'
        final_path = os.path.normpath(final_path)
        
        dir_path = os.path.dirname(final_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
            
        with open(final_path, 'w', encoding='utf-8') as file:
            file.write(content)
            
        logger.info(f"File successfully written to '{final_path}' for agent '{context.agent_id}'.")
        return f"File created/updated at {final_path}"
    except Exception as e:
        logger.error(f"Error writing file to final path '{final_path}' for agent {context.agent_id}: {e}", exc_info=True)
        raise IOError(f"Could not write file at '{final_path}': {str(e)}")
