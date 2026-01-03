"""
Prompt detection for terminal command completion.

Detects when a shell prompt has returned, indicating command completion.
"""

import re
from typing import Optional


class PromptDetector:
    """Detects when shell prompt returns after command execution.
    
    Uses regex pattern matching to identify when the shell has
    returned to a prompt state, indicating command completion.
    """
    
    # Default pattern matches common prompts ending with $ or #
    DEFAULT_PATTERN = r'[\$#]\s*$'
    
    def __init__(self, prompt_pattern: Optional[str] = None):
        """Initialize the prompt detector.
        
        Args:
            prompt_pattern: Regex pattern to match prompt. 
                          Defaults to matching $ or # at end of line.
        """
        self._pattern = prompt_pattern or self.DEFAULT_PATTERN
        self._compiled = re.compile(self._pattern, re.MULTILINE)
    
    def check(self, output: str) -> bool:
        """Check if output ends with a prompt.
        
        Args:
            output: Terminal output to check.
            
        Returns:
            True if output appears to end with a prompt.
        """
        if not output:
            return False
        
        # Check the last few lines for a prompt
        lines = output.rstrip().split('\n')
        if not lines:
            return False
        
        last_line = lines[-1]
        return bool(self._compiled.search(last_line))
    
    def set_pattern(self, pattern: str) -> None:
        """Update the prompt pattern.
        
        Args:
            pattern: New regex pattern to use.
        """
        self._pattern = pattern
        self._compiled = re.compile(self._pattern, re.MULTILINE)
    
    @property
    def pattern(self) -> str:
        """Current prompt pattern."""
        return self._pattern
