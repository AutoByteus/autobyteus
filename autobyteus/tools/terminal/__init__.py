"""
Terminal tools package.

Provides PTY-based terminal operations for agents with stateful
command execution and background process management.
"""

from autobyteus.tools.terminal.types import (
    TerminalResult,
    BackgroundProcessOutput,
    ProcessInfo,
)
from autobyteus.tools.terminal.output_buffer import OutputBuffer
from autobyteus.tools.terminal.prompt_detector import PromptDetector
from autobyteus.tools.terminal.pty_session import PtySession
from autobyteus.tools.terminal.terminal_session_manager import TerminalSessionManager
from autobyteus.tools.terminal.background_process_manager import BackgroundProcessManager

__all__ = [
    # Types
    "TerminalResult",
    "BackgroundProcessOutput",
    "ProcessInfo",
    # Components
    "OutputBuffer",
    "PromptDetector",
    "PtySession",
    "TerminalSessionManager",
    "BackgroundProcessManager",
]
