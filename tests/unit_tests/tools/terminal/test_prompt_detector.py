"""
Unit tests for prompt_detector.py
"""

import pytest
from autobyteus.tools.terminal.prompt_detector import PromptDetector


class TestPromptDetector:
    """Tests for PromptDetector class."""
    
    def test_detects_dollar_prompt(self):
        """Test detection of standard $ prompt."""
        detector = PromptDetector()
        
        assert detector.check("user@host:~$ ")
        assert detector.check("/home/user $ ")
        assert detector.check("$ ")
    
    def test_detects_hash_prompt(self):
        """Test detection of root # prompt."""
        detector = PromptDetector()
        
        assert detector.check("root@host:~# ")
        assert detector.check("# ")
    
    def test_no_prompt_in_output(self):
        """Test returns False when no prompt detected."""
        detector = PromptDetector()
        
        assert not detector.check("some output")
        assert not detector.check("still running...")
        assert not detector.check("")
    
    def test_prompt_after_output(self):
        """Test detection of prompt after command output."""
        detector = PromptDetector()
        
        output = """total 4
drwxr-xr-x 2 user user 4096 Jan  1 00:00 folder
-rw-r--r-- 1 user user    0 Jan  1 00:00 file.txt
user@host:~$ """
        
        assert detector.check(output)
    
    def test_no_prompt_during_command(self):
        """Test returns False for partial output without prompt."""
        detector = PromptDetector()
        
        output = """Installing packages...
[1/10] Installing package A
[2/10] Installing package B"""
        
        assert not detector.check(output)
    
    def test_custom_pattern(self):
        """Test custom prompt pattern."""
        detector = PromptDetector(prompt_pattern=r">>>\s*$")
        
        assert detector.check(">>> ")
        assert not detector.check("$ ")
    
    def test_set_pattern(self):
        """Test changing pattern dynamically."""
        detector = PromptDetector()
        
        assert detector.check("$ ")
        assert not detector.check(">>> ")
        
        detector.set_pattern(r">>>\s*$")
        
        assert not detector.check("$ ")
        assert detector.check(">>> ")
    
    def test_pattern_property(self):
        """Test pattern property returns current pattern."""
        custom = r"custom\s*$"
        detector = PromptDetector(prompt_pattern=custom)
        
        assert detector.pattern == custom
    
    def test_multiline_output_checks_last_line(self):
        """Test that only last line is checked for prompt."""
        detector = PromptDetector()
        
        # Prompt in middle, not at end
        output_no_prompt = """$ ls
file1
file2
still working"""
        assert not detector.check(output_no_prompt)
        
        # Prompt at end
        output_with_prompt = """$ ls
file1
file2
user@host:~$ """
        assert detector.check(output_with_prompt)
    
    def test_trailing_whitespace_variations(self):
        """Test prompt detection with various trailing whitespace."""
        detector = PromptDetector()
        
        assert detector.check("$")
        assert detector.check("$ ")
        assert detector.check("$  ")
        assert detector.check("$ \t")
