# file: autobyteus/autobyteus/tools/file/search_files.py
"""
This module provides a high-performance fuzzy file search tool.
It uses 'git ls-files' for speed in Git repositories and falls back
to a filesystem walk for other directories, respecting .gitignore.
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING

from rapidfuzz import process, fuzz
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from autobyteus.tools.functional_tool import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


@tool(name="search_files", category=ToolCategory.FILE_SYSTEM)
async def search_files(
    context: 'AgentContext',
    query: Optional[str] = None,
    path: str = '.',
    limit: int = 64,
    exclude_patterns: Optional[List[str]] = None
) -> str:
    """
    Performs a high-performance fuzzy search for files in a directory.

    This tool intelligently discovers files. If the search directory is a Git repository,
    it uses the highly efficient 'git ls-files' command. Otherwise, it performs a
    standard filesystem walk. In both cases, it respects .gitignore rules and any
    additional exclusion patterns provided. The search results are returned as a
    JSON string, with each result including the file path and a relevance score.

    Args:
        query: The fuzzy search pattern. If omitted, the tool lists all discoverable files up to the limit.
        path: The directory to search in. Relative paths are resolved against the agent's workspace. Defaults to the workspace root.
        limit: The maximum number of results to return.
        exclude_patterns: A list of glob patterns to exclude from the search, in addition to .gitignore rules.
    """
    final_path = _resolve_search_path(context, path)
    if not final_path.is_dir():
        raise FileNotFoundError(f"The specified search path does not exist or is not a directory: {final_path}")

    exclude = exclude_patterns or []
    files, discovery_method = await _discover_files(final_path, exclude)

    if not query:
        # If no query, just return the first 'limit' files found
        matches = [{"path": f, "score": 100} for f in files[:limit]]
        result_summary = {
            "discovery_method": discovery_method,
            "total_files_scanned": len(files),
            "matches_found": len(matches),
            "results": matches
        }
        return json.dumps(result_summary, indent=2)

    # Use rapidfuzz to find the best matches
    results = process.extract(
        query,
        files,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=50
    )

    file_matches = [{"path": path, "score": round(score)} for path, score, _ in results]
    
    result_summary = {
        "discovery_method": discovery_method,
        "total_files_scanned": len(files),
        "matches_found": len(file_matches),
        "results": file_matches
    }
    return json.dumps(result_summary, indent=2)


def _resolve_search_path(context: 'AgentContext', path: str) -> Path:
    """Resolves the search path against the agent's workspace if relative."""
    if os.path.isabs(path):
        return Path(path)
    
    if not context.workspace:
        raise ValueError(f"Relative path '{path}' provided, but no workspace is configured for agent '{context.agent_id}'.")
    
    base_path = context.workspace.get_base_path()
    if not base_path:
        raise ValueError(f"Agent '{context.agent_id}' has a workspace, but it provided an invalid base path.")
        
    return Path(os.path.normpath(os.path.join(base_path, path)))


async def _is_git_repository_async(path: Path) -> bool:
    """Asynchronously checks if a given path is within a Git repository."""
    process = await asyncio.create_subprocess_exec(
        "git", "rev-parse", "--is-inside-work-tree",
        cwd=str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    return stdout.decode().strip() == "true"


async def _get_files_from_git_async(path: Path) -> List[str]:
    """Uses 'git ls-files' to get a list of all tracked and untracked files."""
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "ls-files", "-co", "--exclude-standard",
            cwd=str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        if process.returncode != 0:
            stderr = stderr_bytes.decode().strip()
            logger.error(f"Failed to run 'git ls-files' in '{path}': {stderr}")
            return []
        
        stdout = stdout_bytes.decode().strip()
        return stdout.strip().split("\n") if stdout.strip() else []
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"Failed to run 'git ls-files': {e}")
        return []


def _get_files_with_walk_sync(path: Path, exclude_patterns: List[str]) -> List[str]:
    """Synchronously walks the filesystem to find files, respecting ignore patterns."""
    files: List[str] = []
    
    all_exclude_patterns = exclude_patterns[:]
    gitignore_path = path / ".gitignore"
    if gitignore_path.is_file():
        try:
            with open(gitignore_path, "r", encoding='utf-8') as f:
                all_exclude_patterns.extend(f.read().splitlines())
        except Exception as e:
            logger.warning(f"Could not read .gitignore file at '{gitignore_path}': {e}")

    spec = PathSpec.from_lines(GitWildMatchPattern, all_exclude_patterns)

    for root, _, filenames in os.walk(path, topdown=True):
        root_path = Path(root)
        for filename in filenames:
            full_path = root_path / filename
            try:
                relative_path = full_path.relative_to(path)
                if not spec.match_file(str(relative_path)):
                    files.append(str(relative_path))
            except (ValueError, IsADirectoryError):
                # Handles cases like broken symlinks
                continue
    return files


async def _get_files_with_walk_async(path: Path, exclude_patterns: List[str]) -> List[str]:
    """Runs the synchronous walk in a thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _get_files_with_walk_sync, path, exclude_patterns
    )


async def _discover_files(cwd: Path, exclude: List[str]) -> Tuple[List[str], str]:
    """Orchestrates the file discovery, choosing between Git and os.walk."""
    if await _is_git_repository_async(cwd):
        logger.info(f"Using 'git ls-files' for fast file discovery in '{cwd}'.")
        files = await _get_files_from_git_async(cwd)
        # Git ls-files already handles gitignore, but we may have extra excludes
        if exclude:
            spec = PathSpec.from_lines(GitWildMatchPattern, exclude)
            files = [f for f in files if not spec.match_file(f)]
        return files, "git"
    else:
        logger.info(f"Using 'os.walk' to scan directory '{cwd}'.")
        return await _get_files_with_walk_async(cwd, exclude), "os_walk"
