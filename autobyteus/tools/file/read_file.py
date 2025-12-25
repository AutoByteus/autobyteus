import os
import logging
from typing import TYPE_CHECKING, Optional

from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

@tool(name="read_file", category=ToolCategory.FILE_SYSTEM)
async def read_file(
    context: 'AgentContext',
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None
) -> str:
    """
    Reads content from a specified file. Supports optional 1-based inclusive line ranges via start_line/end_line.
    Each returned line is prefixed with its line number.
    'path' is the path to the file. If relative, it must be resolved against a configured agent workspace.
    Raises ValueError if a relative path is given without a valid workspace or if line range arguments are invalid.
    Raises FileNotFoundError if the file does not exist.
    Raises IOError if file reading fails for other reasons.
    """
    logger.debug(f"Functional read_file tool for agent {context.agent_id}, initial path: {path}")

    if start_line is not None and start_line < 1:
        raise ValueError(f"start_line must be >= 1 when provided; got {start_line}.")
    if end_line is not None and end_line < 1:
        raise ValueError(f"end_line must be >= 1 when provided; got {end_line}.")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError(f"end_line ({end_line}) must be >= start_line ({start_line}).")
    
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

    # It's good practice to normalize the path to handle things like '..'
    final_path = os.path.normpath(final_path)

    if not os.path.exists(final_path):
        raise FileNotFoundError(f"The file at resolved path {final_path} does not exist.")
        
    try:
        with open(final_path, 'r', encoding='utf-8') as file:
            selected_lines = []
            for line_no, line in enumerate(file, start=1):
                if start_line is not None and line_no < start_line:
                    continue
                if end_line is not None and line_no > end_line:
                    break
                line_text = line.rstrip('\n')
                line_suffix = '\n' if line.endswith('\n') else ''
                selected_lines.append(f"{line_no}: {line_text}{line_suffix}")
            content = ''.join(selected_lines)
        logger.info(f"File successfully read from '{final_path}' for agent '{context.agent_id}'.")
        return content
    except Exception as e:
        logger.error(f"Error reading file from final path '{final_path}' for agent {context.agent_id}: {e}", exc_info=True)
        raise IOError(f"Could not read file at {final_path}: {str(e)}")
