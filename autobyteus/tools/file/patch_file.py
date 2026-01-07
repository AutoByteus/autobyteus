import os
import logging
from typing import TYPE_CHECKING, List

from autobyteus.tools.functional_tool import tool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.diff_utils import apply_unified_diff, PatchApplicationError

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)


def _resolve_file_path(context: 'AgentContext', path: str) -> str:
    """Resolves an absolute path for the given input, using the agent workspace when needed."""
    if os.path.isabs(path):
        final_path = path
        logger.debug("patch_file: provided path '%s' is absolute.", path)
    else:
        if not context.workspace:
            error_msg = ("Relative path '%s' provided, but no workspace is configured for agent '%s'. "
                         "A workspace is required to resolve relative paths.")
            logger.error(error_msg, path, context.agent_id)
            raise ValueError(error_msg % (path, context.agent_id))
        base_path = context.workspace.get_base_path()
        if not base_path or not isinstance(base_path, str):
            error_msg = ("Agent '%s' has a configured workspace, but it provided an invalid base path ('%s'). "
                         "Cannot resolve relative path '%s'.")
            logger.error(error_msg, context.agent_id, base_path, path)
            raise ValueError(error_msg % (context.agent_id, base_path, path))
        final_path = os.path.join(base_path, path)
        logger.debug("patch_file: resolved relative path '%s' against workspace base '%s' to '%s'.", path, base_path, final_path)

    normalized_path = os.path.normpath(final_path)
    logger.debug("patch_file: normalized path to '%s'.", normalized_path)
    return normalized_path


@tool(name="patch_file", category=ToolCategory.FILE_SYSTEM)
async def patch_file(context: 'AgentContext', path: str, patch: str) -> str:
    """Applies a unified diff patch to update a text file without overwriting unrelated content.

    Args:
        path: Path to the target file. Relative paths are resolved against the agent workspace when available.
        patch: Unified diff patch describing the edits to apply.

    Raises:
        FileNotFoundError: If the file does not exist.
        PatchApplicationError: If the patch content cannot be applied cleanly.
        IOError: If file reading or writing fails.
    """
    logger.debug("patch_file: requested patch for agent '%s' on path '%s'.", context.agent_id, path)
    final_path = _resolve_file_path(context, path)

    file_exists = os.path.exists(final_path)
    if not file_exists:
        raise FileNotFoundError(f"The file at resolved path {final_path} does not exist.")

    try:
        original_lines: List[str]
        if file_exists:
            with open(final_path, 'r', encoding='utf-8') as source:
                original_lines = source.read().splitlines(keepends=True)
        else:
            original_lines = []

        patched_lines = apply_unified_diff(original_lines, patch)

        with open(final_path, 'w', encoding='utf-8') as destination:
            destination.writelines(patched_lines)

        logger.info("patch_file: successfully applied patch to '%s'.", final_path)
        return f"File patched successfully at {final_path}"
    except PatchApplicationError as patch_err:
        logger.error("patch_file: failed to apply patch to '%s': %s", final_path, patch_err, exc_info=True)
        raise patch_err
    except Exception as exc:  # pragma: no cover - general safeguard
        logger.error("patch_file: unexpected error while patching '%s': %s", final_path, exc, exc_info=True)
        raise IOError(f"Could not patch file at '{final_path}': {exc}")
