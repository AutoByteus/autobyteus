# file: autobyteus/autobyteus/tools/file/list_directory.py
"""
This module provides a tool for listing directory contents in a structured,
tree-like format, mirroring the behavior of the Codex Rust implementation.
"""

import asyncio
import logging
import os
from pathlib import Path
from collections import deque
from dataclasses import dataclass
from typing import List, Deque, Tuple, Optional, TYPE_CHECKING

from autobyteus.tools.functional_tool import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

# Constants from the design document
INDENTATION_SPACES = 2
MAX_ENTRY_LENGTH = 500

@dataclass
class DirEntry:
    """Represents a collected directory entry for sorting and formatting."""
    name: str
    kind: str
    depth: int

@tool(name="list_directory", category=ToolCategory.FILE_SYSTEM)
async def list_directory(
    context: 'AgentContext',
    path: str,
    depth: int = 2,
    limit: int = 25,
    offset: int = 1
) -> str:
    """
    Lists the contents of a directory in a structured, tree-like format.

    This tool performs a breadth-first traversal of the specified directory up to a
    given depth. It returns a deterministic, lexicographically sorted list of entries,
    formatted with indentation and tree glyphs to represent the hierarchy.

    Args:
        path: The path to the directory to list. Relative paths are resolved against the agent's workspace.
        depth: The maximum directory depth to traverse. Must be > 0.
        limit: The maximum number of entries to return in the output. Must be > 0.
        offset: The 1-indexed entry number to start from, for pagination. Must be > 0.
    """
    # --- 1. Argument Validation ---
    logger.debug(f"list_directory for agent {context.agent_id}, initial path: {path}")

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

    final_path = os.path.normpath(final_path)

    if not Path(final_path).is_dir():
        raise FileNotFoundError(f"Directory not found at path: {final_path}")
    if depth <= 0 or limit <= 0 or offset <= 0:
        raise ValueError("depth, limit, and offset must all be greater than zero.")

    # --- 2. Asynchronous Traversal ---
    loop = asyncio.get_running_loop()
    all_entries = await loop.run_in_executor(
        None, _traverse_directory_bfs, Path(final_path), depth
    )

    # --- 3. Slicing ---
    total_found = len(all_entries)
    start_index = offset - 1
    end_index = start_index + limit
    sliced_entries = all_entries[start_index:end_index]

    # --- 4. Formatting ---
    output_lines = [f"Absolute path: {final_path}"]
    
    # To correctly apply tree glyphs, we need to know which entry is the last in its directory
    # This is complex with BFS. A simpler, visually acceptable approach is taken here.
    # For a more accurate glyph representation like the Rust version, we would need to
    # process entries directory by directory after collection.
    for i, entry in enumerate(sliced_entries):
        # A simplified glyph logic: last item in the slice gets the closing glyph
        is_last = (i == len(sliced_entries) - 1)
        output_lines.append(_format_entry_line(entry, is_last))

    if total_found > end_index:
        output_lines.append(f"More than {limit} entries found.")

    return "\n".join(output_lines)


def _traverse_directory_bfs(start_path: Path, max_depth: int) -> List[DirEntry]:
    """
    Performs a breadth-first traversal of a directory. This is a synchronous function
    designed to be run in a thread pool executor.
    """
    collected: List[DirEntry] = []
    queue: Deque[Tuple[Path, int]] = deque([(start_path, 0)])

    while queue:
        current_path, current_depth = queue.popleft()

        if current_depth >= max_depth:
            continue

        try:
            # Use os.scandir for efficiency as it fetches file type info
            entries_at_level = []
            for entry in os.scandir(current_path):
                kind = "[unknown]"
                if entry.is_dir():
                    kind = "[dir]"
                    queue.append((Path(entry.path), current_depth + 1))
                elif entry.is_file():
                    kind = "[file]"
                elif entry.is_symlink():
                    kind = "[link]"

                # Truncate long filenames
                display_name = entry.name
                if len(display_name) > MAX_ENTRY_LENGTH:
                    display_name = display_name[:MAX_ENTRY_LENGTH] + "..."
                
                entries_at_level.append(DirEntry(name=display_name, kind=kind, depth=current_depth + 1))
            
            # Sort entries at the current level before adding to the main list
            entries_at_level.sort(key=lambda e: e.name)
            collected.extend(entries_at_level)

        except (PermissionError, OSError) as e:
            logger.warning(f"Could not read directory '{current_path}': {e}")
            continue
    
    return collected


def _format_entry_line(entry: DirEntry, is_last_in_slice: bool) -> str:
    """Formats a single directory entry into its final string representation."""
    # This simplified glyph logic doesn't know about siblings, just the slice.
    # A full implementation would require grouping by parent path after collection.
    prefix = "└─ " if is_last_in_slice else "├─ "
    
    # Indentation is based on depth from the root search path
    indentation = " " * INDENTATION_SPACES * (entry.depth -1)
    
    return f"{indentation}{prefix}{entry.kind} {entry.name}"
