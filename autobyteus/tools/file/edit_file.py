import os
import re
import logging
from typing import TYPE_CHECKING, List

from autobyteus.tools.functional_tool import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

_HUNK_HEADER_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")

class PatchApplicationError(ValueError):
    """Raised when a unified diff patch cannot be applied to the target file."""


def _resolve_file_path(context: 'AgentContext', path: str) -> str:
    """Resolves an absolute path for the given input, using the agent workspace when needed."""
    if os.path.isabs(path):
        final_path = path
        logger.debug("edit_file: provided path '%s' is absolute.", path)
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
        logger.debug("edit_file: resolved relative path '%s' against workspace base '%s' to '%s'.", path, base_path, final_path)

    normalized_path = os.path.normpath(final_path)
    logger.debug("edit_file: normalized path to '%s'.", normalized_path)
    return normalized_path


def _apply_unified_diff(original_lines: List[str], patch: str) -> List[str]:
    """Applies a unified diff patch to the provided original lines and returns the patched lines."""
    if not patch or not patch.strip():
        raise PatchApplicationError("Patch content is empty; nothing to apply.")

    patched_lines: List[str] = []
    orig_idx = 0
    patch_lines = patch.splitlines(keepends=True)
    line_idx = 0

    while line_idx < len(patch_lines):
        line = patch_lines[line_idx]

        if line.startswith('---') or line.startswith('+++'):
            logger.debug("edit_file: skipping diff header line '%s'.", line.strip())
            line_idx += 1
            continue

        if not line.startswith('@@'):
            stripped = line.strip()
            if stripped == '':
                line_idx += 1
                continue
            raise PatchApplicationError(f"Unexpected content outside of hunk header: '{stripped}'.")

        match = _HUNK_HEADER_RE.match(line)
        if not match:
            raise PatchApplicationError(f"Malformed hunk header: '{line.strip()}'.")

        old_start = int(match.group('old_start'))
        old_count = int(match.group('old_count') or '1')
        new_start = int(match.group('new_start'))
        new_count = int(match.group('new_count') or '1')
        logger.debug("edit_file: processing hunk old_start=%s old_count=%s new_start=%s new_count=%s.",
                     old_start, old_count, new_start, new_count)

        target_idx = old_start - 1 if old_start > 0 else 0
        if target_idx > len(original_lines):
            raise PatchApplicationError("Patch hunk starts beyond end of file.")
        if target_idx < orig_idx:
            raise PatchApplicationError("Patch hunks overlap or are out of order.")

        patched_lines.extend(original_lines[orig_idx:target_idx])
        orig_idx = target_idx

        line_idx += 1
        hunk_consumed = 0
        removed = 0
        added = 0

        while line_idx < len(patch_lines):
            hunk_line = patch_lines[line_idx]
            if hunk_line.startswith('@@'):
                break

            if hunk_line.startswith('-'):
                if orig_idx >= len(original_lines):
                    raise PatchApplicationError("Patch attempts to remove lines beyond file length.")
                if original_lines[orig_idx] != hunk_line[1:]:
                    raise PatchApplicationError("Patch removal does not match file content.")
                orig_idx += 1
                hunk_consumed += 1
                removed += 1
            elif hunk_line.startswith('+'):
                patched_lines.append(hunk_line[1:])
                added += 1
            elif hunk_line.startswith(' '):
                if orig_idx >= len(original_lines):
                    raise PatchApplicationError("Patch context exceeds file length.")
                if original_lines[orig_idx] != hunk_line[1:]:
                    raise PatchApplicationError("Patch context does not match file content.")
                patched_lines.append(original_lines[orig_idx])
                orig_idx += 1
                hunk_consumed += 1
            elif hunk_line.startswith('\\'):
                if hunk_line.strip() == '\\ No newline at end of file':
                    if patched_lines:
                        patched_lines[-1] = patched_lines[-1].rstrip('\n')
                else:
                    raise PatchApplicationError(f"Unsupported patch directive: '{hunk_line.strip()}'.")
            elif hunk_line.strip() == '':
                patched_lines.append(hunk_line)
            else:
                raise PatchApplicationError(f"Unsupported patch line: '{hunk_line.strip()}'.")

            line_idx += 1

        consumed_total = hunk_consumed
        if old_count == 0:
            if consumed_total != 0:
                raise PatchApplicationError("Patch expects zero original lines but consumed some context.")
        else:
            if consumed_total != old_count:
                raise PatchApplicationError(
                    f"Patch expected to consume {old_count} original lines but consumed {consumed_total}.")

        context_lines = consumed_total - removed
        expected_new_lines = context_lines + added
        if new_count == 0:
            if expected_new_lines != 0:
                raise PatchApplicationError("Patch declares zero new lines but produced changes.")
        else:
            if expected_new_lines != new_count:
                raise PatchApplicationError(
                    f"Patch expected to produce {new_count} new lines but produced {expected_new_lines}.")

    patched_lines.extend(original_lines[orig_idx:])
    return patched_lines


@tool(name="edit_file", category=ToolCategory.FILE_SYSTEM)
async def edit_file(context: 'AgentContext', path: str, patch: str, create_if_missing: bool = False) -> str:
    """Applies a unified diff patch to update a text file without overwriting unrelated content.

    Args:
        path: Path to the target file. Relative paths are resolved against the agent workspace when available.
        patch: Unified diff patch describing the edits to apply.
        create_if_missing: When True, allows applying a patch that introduces content to a non-existent file.

    Raises:
        FileNotFoundError: If the file does not exist and create_if_missing is False.
        PatchApplicationError: If the patch content cannot be applied cleanly.
        IOError: If file reading or writing fails.
    """
    logger.debug("edit_file: requested edit for agent '%s' on path '%s'.", context.agent_id, path)
    final_path = _resolve_file_path(context, path)

    dir_path = os.path.dirname(final_path)
    if dir_path and not os.path.exists(dir_path) and create_if_missing:
        os.makedirs(dir_path, exist_ok=True)

    file_exists = os.path.exists(final_path)
    if not file_exists and not create_if_missing:
        raise FileNotFoundError(f"The file at resolved path {final_path} does not exist.")

    try:
        original_lines: List[str]
        if file_exists:
            with open(final_path, 'r', encoding='utf-8') as source:
                original_lines = source.read().splitlines(keepends=True)
        else:
            original_lines = []

        patched_lines = _apply_unified_diff(original_lines, patch)

        with open(final_path, 'w', encoding='utf-8') as destination:
            destination.writelines(patched_lines)

        logger.info("edit_file: successfully applied patch to '%s'.", final_path)
        return f"File edited successfully at {final_path}"
    except PatchApplicationError as patch_err:
        logger.error("edit_file: failed to apply patch to '%s': %s", final_path, patch_err, exc_info=True)
        raise patch_err
    except Exception as exc:  # pragma: no cover - general safeguard
        logger.error("edit_file: unexpected error while editing '%s': %s", final_path, exc, exc_info=True)
        raise IOError(f"Could not edit file at '{final_path}': {exc}")
