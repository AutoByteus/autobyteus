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


def apply_unified_diff(
    original_lines: List[str], 
    patch: str, 
    fuzz_factor: int = 0, 
    ignore_whitespace: bool = False
) -> List[str]:
    """Applies a unified diff patch to the provided original lines and returns the patched lines.
    
    Args:
        original_lines: List of strings representing the original content lines (with line endings preserved).
        patch: Unified diff patch string describing the edits to apply.
        fuzz_factor: Number of lines to search up/down if exact line number match fails.
        ignore_whitespace: If True, ignores leading/trailing whitespace when matching context.
        
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

    def lines_match(l1: str, l2: str) -> bool:
        if ignore_whitespace:
            return l1.strip() == l2.strip()
        return l1 == l2

    while line_idx < len(patch_lines):
        line = patch_lines[line_idx]

        if line.startswith('---') or line.startswith('+++'):
            logger.debug("apply_unified_diff: skipping diff header line '%s'.", line.strip())
            line_idx += 1
            continue

        if not line.startswith('@@'):
            stripped = line.strip()
            if stripped == '':
                # Handle empty lines between hunks or at start as noise, but
                # legacy behavior might have been to append them?
                # The previous loop skipped them if start of file (implicit in while loop start?), 
                # but inside the hunk loop it appended them.
                # Here we are searching for hunk headers.
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
        
        line_idx += 1 # Move past header
        
        # Capture the hunk body
        hunk_body = []
        while line_idx < len(patch_lines):
            h_line = patch_lines[line_idx]
            if h_line.startswith('@@'):
                break
            hunk_body.append(h_line)
            line_idx += 1
            
        # Extract expected original content from hunk
        # We process the hunk body to confirm what we expect to see in original_lines
        refined_expected_orig = []
        h_i = 0
        while h_i < len(hunk_body):
            h_line = hunk_body[h_i]
            if h_line.startswith(' ') or h_line.startswith('-'):
                content = h_line[1:]
                # Check next line for '\ No newline...' to handle EOF correctly during match
                if h_i + 1 < len(hunk_body) and hunk_body[h_i+1].startswith('\\ No newline'):
                    content = content.rstrip('\n')
                elif h_i + 1 == len(hunk_body) and not content.endswith('\n'):
                     # Last line of patch might legitimately not have newline? 
                     # Usually lines have newlines. If it's a file without newline at end, diff shows \ No newline.
                     pass
                refined_expected_orig.append(content)
            elif h_line.startswith('+'):
                pass
            elif h_line.startswith('\\'):
                pass 
            elif h_line.strip() == '':
                 # Treat bare empty line as non-match content (noise/insert)?
                 # Previous code appended it to output but didn't check against input.
                 # So we do NOT add to refined_expected_orig.
                 pass
            else:
                 raise PatchApplicationError(f"Unsupported patch line: '{h_line.strip()}'.")
            h_i += 1

        expected_count = len(refined_expected_orig)

        # Fuzzy Search for Match
        # Ideally target is old_start - 1 (converting 1-based old_start to 0-based index)
        target_idx_base = old_start - 1 if old_start > 0 else 0
        
        found_idx = -1
        
        # Generate search offsets: 0, -1, 1, -2, 2, ...
        offsets = [0]
        for f in range(1, fuzz_factor + 1):
            offsets.append(-f)
            offsets.append(f)
            
        for offset in offsets:
            candidate_idx = target_idx_base + offset
            
            # Constraints:
            # 1. Must proceed forward from where we left off (orig_idx)
            # 2. Must not go beyond EOF (handled by slicing)
            if candidate_idx < orig_idx:
                continue 
            
            # Check if this candidate location matches expected_orig
            # We need to verify that original_lines[candidate_idx : candidate_idx + expected_count] matches refined_expected_orig
            
            if candidate_idx + expected_count > len(original_lines):
                # Ensure we don't go out of bounds (though partial match at EOF might be a thing? No, hunk must match fully)
                continue

            match_success = True
            for k in range(expected_count):
                # Note: lines_match handles whitespace if needed.
                if not lines_match(original_lines[candidate_idx + k], refined_expected_orig[k]):
                    match_success = False
                    break
            
            if match_success:
                found_idx = candidate_idx
                break
                
        if found_idx == -1:
             raise PatchApplicationError(f"Could not find context for hunk starting at {old_start} (fuzz={fuzz_factor}).")
             
        # Apply changes
        
        # 1. Copy lines from orig_idx to found_idx (these are the lines BEFORE the hunk that we skipped over/accepted)
        patched_lines.extend(original_lines[orig_idx:found_idx])
        
        # 2. Process hunk body to generate new lines
        h_i = 0
        while h_i < len(hunk_body):
            h_line = hunk_body[h_i]
            if h_line.startswith(' ') or h_line.startswith('-'):
                # Valid context or removal - we skip them in output (they are either preserved via context or removed)
                # If context (' '), we should actually append the ORIGINAL line to allow for fuzziness?
                # Standard patch behavior: if fuzz matches, we output the *hunk's* version of the line? 
                # OR we output the *original* file's version?
                # `patch` man page says: "patch takes the context from the diff file"
                # Wait, if we fuzzy matched, likely we want to keep what was in the file unless the patch explicitly changes it.
                # However, typically ' ' lines are just copied.
                # If we use `patched_lines.append(original_lines[found_idx + handled_count])`, that preserves the file's indentation/whitespace.
                # If we use `h_line[1:]`, we enforce the patch's indentation.
                # Requirement: "Ignore Whitespace... Allow context comparisons to ignore...".
                # If the patch "autocorrects" indentation in context lines, we probably want to KEEP the file's original indentation 
                # for context lines, so we don't accidentally "fix" them if we aren't touching them.
                # Unified diff: ' ' means "unchanged". So we should emit the *original* line.
                
                if h_line.startswith(' '):
                    # Find which original line this corresponds to.
                    # We are iterating h_i through hunk_body.
                    # We need to track our position in the matched original block.
                    # Let's track `current_match_offset`
                    pass 
            elif h_line.startswith('+'):
                pass
            h_i += 1
            
        # Let's redo step 2 cleanly to handle the ' ' vs '-' vs '+' and the '\ No newline' logic.
        
        matched_orig_offset = 0 # Offset into the matched block of original_lines [found_idx : found_idx+expected_count]
        
        h_i = 0
        while h_i < len(hunk_body):
            h_line = hunk_body[h_i]
            
            if h_line.startswith(' '):
                # Context line: preserve original content from file
                if found_idx + matched_orig_offset < len(original_lines):
                    patched_lines.append(original_lines[found_idx + matched_orig_offset])
                matched_orig_offset += 1
                
            elif h_line.startswith('-'):
                # Removal: skip original content
                matched_orig_offset += 1
                
            elif h_line.startswith('+'):
                # Addition: add content from patch
                content = h_line[1:]
                if h_i + 1 < len(hunk_body) and hunk_body[h_i+1].startswith('\\ No newline'):
                    content = content.rstrip('\n')
                patched_lines.append(content)
                
            elif h_line.strip() == '':
                 # "Empty" line in patch. Legacy behavior: append to output. 
                 # Does not consume original.
                 patched_lines.append(h_line)
                 
            elif h_line.startswith('\\'):
                 # No newline marker, handled by lookahead in + case. 
                 # For - and space, we used original lines so their newline status is preserved automatically!
                 pass
                 
            h_i += 1
            
        orig_idx = found_idx + expected_count

    patched_lines.extend(original_lines[orig_idx:])
    return patched_lines
