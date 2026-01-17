"""
Unit tests for session_factory.py
"""

from autobyteus.tools.terminal import session_factory


def test_get_default_session_factory_windows(monkeypatch):
    """Windows should use WslTmuxSession."""
    monkeypatch.setattr(session_factory, "_is_windows", lambda: True)

    factory = session_factory.get_default_session_factory()

    assert factory.__name__ == "WslTmuxSession"


def test_get_default_session_factory_posix(monkeypatch):
    """Non-Windows should use PtySession."""
    monkeypatch.setattr(session_factory, "_is_windows", lambda: False)

    factory = session_factory.get_default_session_factory()

    assert factory.__name__ == "PtySession"
