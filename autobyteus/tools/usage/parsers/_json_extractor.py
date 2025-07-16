import re
import logging
from typing import List

logger = logging.getLogger(__name__)

def _find_json_blobs(text: str) -> List[str]:
    """
    Robustly finds and extracts all top-level JSON objects or arrays from a string,
    maintaining their original order of appearance. It handles JSON within
    markdown-style code blocks (```json ... ```) and inline JSON.
    
    Args:
        text: The string to search for JSON in.
        
    Returns:
        A list of strings, where each string is a valid-looking JSON blob,
        ordered as they appeared in the input text.
    """
    found_blobs = []

    # 1. Find all markdown blobs first and store them with their start positions.
    markdown_matches = list(re.finditer(r"```(?:json)?\s*([\s\S]+?)\s*```", text))
    for match in markdown_matches:
        content = match.group(1).strip()
        found_blobs.append((match.start(), content))
    
    # 2. Create a "masked" version of the text by replacing markdown blocks with spaces.
    #    This prevents the inline scanner from finding JSON inside them, while preserving indices.
    masked_text_list = list(text)
    for match in markdown_matches:
        for i in range(match.start(), match.end()):
            masked_text_list[i] = ' '
    masked_text = "".join(masked_text_list)

    # 3. Scan the masked text for any other JSON using a single pass brace-counter.
    idx = 0
    while idx < len(masked_text):
        start_idx = -1
        
        # Find the next opening brace or bracket
        next_brace = masked_text.find('{', idx)
        next_bracket = masked_text.find('[', idx)

        if next_brace == -1 and next_bracket == -1:
            break # No more JSON starts
        
        if next_brace != -1 and (next_bracket == -1 or next_brace < next_bracket):
            start_idx = next_brace
            start_char, end_char = '{', '}'
        else:
            start_idx = next_bracket
            start_char, end_char = '[', ']'

        brace_count = 1
        in_string = False
        is_escaped = False
        end_idx = -1

        for i in range(start_idx + 1, len(masked_text)):
            char = masked_text[i]
            
            if in_string:
                if is_escaped:
                    is_escaped = False
                elif char == '\\':
                    is_escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                    is_escaped = False
                elif char == '{' or char == '[':
                    brace_count += 1
                elif char == '}' or char == ']':
                    brace_count -= 1
            
            if brace_count == 0:
                if (start_char == '{' and char == '}') or \
                   (start_char == '[' and char == ']'):
                    end_idx = i
                    break
        
        if end_idx != -1:
            # We found a blob in the masked text, so its indices are correct
            # for the original text. Extract the blob from the original text.
            blob = text[start_idx : end_idx + 1]
            found_blobs.append((start_idx, blob))
            idx = end_idx + 1
        else:
            # No matching end brace found, move on from the start character.
            idx = start_idx + 1

    # 4. Sort all found blobs by their start position to ensure correct order
    found_blobs.sort(key=lambda item: item[0])
    
    # 5. Return only the content of the blobs
    return [content for _, content in found_blobs]
