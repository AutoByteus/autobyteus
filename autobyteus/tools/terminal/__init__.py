"""
Terminal tools package.

Provides PTY-based terminal operations for agents with stateful
command execution and background process management.
"""

import os

from autobyteus.tools.terminal.types import (
    TerminalResult,
    BackgroundProcessOutput,
    ProcessInfo,
)
from autobyteus.tools.terminal.output_buffer import OutputBuffer
from autobyteus.tools.terminal.prompt_detector import PromptDetector
from autobyteus.tools.terminal.terminal_session_manager import TerminalSessionManager
from autobyteus.tools.terminal.background_process_manager import BackgroundProcessManager
from autobyteus.tools.terminal.session_factory import get_default_session_factory

PtySession = None
WslPtySession = None

if os.name != "nt":
    from autobyteus.tools.terminal.pty_session import PtySession
else:
    from autobyteus.tools.terminal.wsl_pty_session import WslPtySession

__all__ = [
    # Types
    "TerminalResult",
    "BackgroundProcessOutput",
    "ProcessInfo",
    # Components
    "OutputBuffer",
    "PromptDetector",
    "TerminalSessionManager",
    "BackgroundProcessManager",
    "get_default_session_factory",
]

if PtySession is not None:
    __all__.append("PtySession")
if WslPtySession is not None:
    __all__.append("WslPtySession")
