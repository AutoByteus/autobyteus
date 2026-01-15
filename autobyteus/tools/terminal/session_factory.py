"""
Session factory selection for terminal backends.
"""

import os


def _is_windows() -> bool:
    """Return True if running on Windows."""
    return os.name == "nt"


def get_default_session_factory():
    """Return the default PTY session class for the current platform."""
    if _is_windows():
        from autobyteus.tools.terminal.wsl_pty_session import WslPtySession
        return WslPtySession

    from autobyteus.tools.terminal.pty_session import PtySession
    return PtySession
