"""
WSL utilities for Windows terminal backend.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
from typing import List, Optional


_WSL_MISSING_MESSAGE = (
    "WSL is not available. Install it with `wsl --install` and reboot, "
    "then ensure a Linux distro is installed."
)


def find_wsl_executable() -> Optional[str]:
    """Return the path to wsl.exe (preferred) or wsl if available."""
    return shutil.which("wsl.exe") or shutil.which("wsl")


def ensure_wsl_available() -> str:
    """Return the WSL executable path or raise with guidance."""
    wsl_exe = find_wsl_executable()
    if not wsl_exe:
        raise RuntimeError(_WSL_MISSING_MESSAGE)
    return wsl_exe


def list_wsl_distros(wsl_exe: str) -> List[str]:
    """Return a list of installed WSL distro names."""
    result = subprocess.run(
        [wsl_exe, "-l", "-q"],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def ensure_wsl_distro_available(wsl_exe: str) -> None:
    """Raise if no WSL distro is installed."""
    distros = list_wsl_distros(wsl_exe)
    if not distros:
        raise RuntimeError(
            "No WSL distro is installed. Run `wsl --install` "
            "or install a distro from the Microsoft Store."
        )


def _run_wslpath(wsl_exe: str, path: str) -> Optional[str]:
    """Try to convert a Windows path to WSL path via wslpath."""
    result = subprocess.run(
        [wsl_exe, "wslpath", "-a", "-u", path],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def _manual_windows_path_to_wsl(path: str) -> str:
    """Manual conversion for Windows drive paths to /mnt/<drive>/..."""
    windows_path = pathlib.PureWindowsPath(path)

    if windows_path.drive:
        drive_letter = windows_path.drive.rstrip(":").lower()
        parts = windows_path.parts[1:]  # strip drive
        if parts:
            return f"/mnt/{drive_letter}/" + "/".join(parts)
        return f"/mnt/{drive_letter}"

    raise ValueError(f"Unsupported Windows path format: {path}")


def windows_path_to_wsl(path: str, wsl_exe: Optional[str] = None) -> str:
    """Convert a Windows path to a WSL path, with wslpath fallback."""
    if not path:
        raise ValueError("Path must be a non-empty string.")

    if path.startswith("/"):
        return path

    if path.startswith("\\\\"):
        raise ValueError("UNC paths are not supported for WSL conversion.")

    if wsl_exe is None:
        wsl_exe = ensure_wsl_available()

    wslpath = _run_wslpath(wsl_exe, path)
    if wslpath:
        return wslpath

    return _manual_windows_path_to_wsl(path)
