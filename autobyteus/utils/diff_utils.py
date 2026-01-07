"""
Unified diff utilities for applying patches to text content.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

_HUNK_HEADER_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@")


class PatchApplicationError(ValueError):
    """Raised when a unified diff patch cannot be applied to the target content."""


def apply_unified_diff(original_lines: List[str], patch: str) -> List[str]:
    """Applies a unified diff patch to the provided original lines and returns the patched lines.
    
    Args:
        original_lines: List of strings representing the original content lines (with line endings preserved).
        patch: Unified diff patch string describing the edits to apply.
        
    Returns:
        List of strings representing the patched content lines.
        
    Raises:
        PatchApplicationError: If the patch content cannot be applied cleanly.
    """
    if not patch or not patch.strip():
        raise PatchApplicationError("Patch content is empty; nothing to apply.")

    patched_lines: List[str] = []
    orig_idx = 0
    patch_lines = patch.splitlines(keepends=True)
    line_idx = 0

    while line_idx < len(patch_lines):
        line = patch_lines[line_idx]

        if line.startswith('---') or line.startswith('+++'):
            logger.debug("apply_unified_diff: skipping diff header line '%s'.", line.strip())
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
        logger.debug("apply_unified_diff: processing hunk old_start=%s old_count=%s new_start=%s new_count=%s.",
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
