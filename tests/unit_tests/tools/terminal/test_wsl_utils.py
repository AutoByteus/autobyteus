"""
Unit tests for wsl_utils.py
"""

import pytest

from autobyteus.tools.terminal import wsl_utils


def test_find_wsl_executable_prefers_wsl_exe(monkeypatch):
    """Prefer wsl.exe when both are available."""
    def fake_which(name: str):
        if name == "wsl.exe":
            return r"C:\Windows\System32\wsl.exe"
        if name == "wsl":
            return r"C:\Windows\System32\wsl"
        return None

    monkeypatch.setattr(wsl_utils.shutil, "which", fake_which)

    assert wsl_utils.find_wsl_executable() == r"C:\Windows\System32\wsl.exe"


def test_find_wsl_executable_falls_back_to_wsl(monkeypatch):
    """Fallback to wsl when wsl.exe is not found."""
    def fake_which(name: str):
        if name == "wsl.exe":
            return None
        if name == "wsl":
            return r"C:\Windows\System32\wsl"
        return None

    monkeypatch.setattr(wsl_utils.shutil, "which", fake_which)

    assert wsl_utils.find_wsl_executable() == r"C:\Windows\System32\wsl"


def test_ensure_wsl_available_raises(monkeypatch):
    """ensure_wsl_available raises when no WSL executable is found."""
    monkeypatch.setattr(wsl_utils.shutil, "which", lambda _: None)

    with pytest.raises(RuntimeError, match="WSL is not available"):
        wsl_utils.ensure_wsl_available()


def test_windows_path_to_wsl_uses_wslpath(monkeypatch):
    """If wslpath succeeds, its output is used."""
    monkeypatch.setattr(wsl_utils, "_run_wslpath", lambda *_: "/mnt/c/Users/me/proj")

    result = wsl_utils.windows_path_to_wsl(r"C:\Users\me\proj", wsl_exe="wsl.exe")

    assert result == "/mnt/c/Users/me/proj"


def test_windows_path_to_wsl_manual_fallback(monkeypatch):
    """Fallback to manual conversion when wslpath fails."""
    monkeypatch.setattr(wsl_utils, "_run_wslpath", lambda *_: None)

    result = wsl_utils.windows_path_to_wsl(r"C:\Users\me\proj", wsl_exe="wsl.exe")

    assert result == "/mnt/c/Users/me/proj"


def test_windows_path_to_wsl_unc_raises(monkeypatch):
    """UNC paths are rejected with a helpful error."""
    monkeypatch.setattr(wsl_utils, "_run_wslpath", lambda *_: None)

    with pytest.raises(ValueError, match="UNC paths are not supported"):
        wsl_utils.windows_path_to_wsl(r"\\server\share\proj", wsl_exe="wsl.exe")
