"""
ANSI escape sequence utilities for cleaning terminal output.
"""

import re

# Regex pattern for ANSI escape sequences
# Matches: ESC[...m (colors), ESC[...H (cursor), etc.
_ANSI_ESCAPE_PATTERN = re.compile(r'\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07|\x1b[=>]')


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from text.
    
    Strips color codes, cursor control, and other terminal escape
    sequences, leaving only the plain text content.
    
    Args:
        text: String potentially containing ANSI escape codes.
        
    Returns:
        Clean string with ANSI codes removed.
        
    Examples:
        >>> strip_ansi_codes('\x1b[31mRed text\x1b[0m')
        'Red text'
        >>> strip_ansi_codes('Hello\x1b[1;32m World\x1b[0m')
        'Hello World'
    """
    if not text:
        return text
    return _ANSI_ESCAPE_PATTERN.sub('', text)
