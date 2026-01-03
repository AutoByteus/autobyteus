"""
Data types for terminal tools.

Contains result types returned by terminal operations.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TerminalResult:
    """Result from run_terminal_cmd.
    
    Attributes:
        stdout: Standard output captured from the command.
        stderr: Standard error captured from the command (may be mixed with stdout in PTY).
        exit_code: Exit code if available, None if not captured.
        timed_out: True if command exceeded timeout.
    """
    stdout: str
    stderr: str
    exit_code: Optional[int]
    timed_out: bool


@dataclass
class BackgroundProcessOutput:
    """Result from get_process_output.
    
    Attributes:
        output: Recent output lines from the process.
        is_running: True if process is still running.
        process_id: The process identifier.
    """
    output: str
    is_running: bool
    process_id: str


@dataclass
class ProcessInfo:
    """Information about a background process.
    
    Attributes:
        process_id: Unique identifier for the process.
        command: The command that was executed.
        started_at: Unix timestamp when process started.
        is_running: True if process is still running.
    """
    process_id: str
    command: str
    started_at: float
    is_running: bool
