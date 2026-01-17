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


def _decode_wsl_bytes(raw: bytes) -> str:
    """Decode WSL output that may be UTF-16LE on Windows consoles."""
    if not raw:
        return ""
    if b"\x00" in raw:
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


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
        text=False,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return []
    output = _decode_wsl_bytes(result.stdout)
    return [line.strip() for line in output.splitlines() if line.strip()]


def get_default_wsl_distro(wsl_exe: str) -> Optional[str]:
    """Return the default WSL distro name if available."""
    result = subprocess.run(
        [wsl_exe, "-l", "-v"],
        capture_output=True,
        text=False,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    output = _decode_wsl_bytes(result.stdout)
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            parts = stripped.split()
            if len(parts) >= 2:
                return parts[1]
    return None


def select_wsl_distro(wsl_exe: str) -> str:
    """Select a usable WSL distro, preferring non-Docker defaults."""
    distros = list_wsl_distros(wsl_exe)
    if not distros:
        raise RuntimeError(
            "No WSL distro is installed. Run `wsl --install` "
            "or install a distro from the Microsoft Store."
        )

    default = get_default_wsl_distro(wsl_exe)
    excluded = {"docker-desktop", "docker-desktop-data"}

    if default and default not in excluded:
        return default

    for distro in distros:
        if distro and distro not in excluded:
            return distro

    return default or distros[0]


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
        text=False,
        check=False,
        timeout=5,
    )
    if result.returncode != 0:
        return None
    output = _decode_wsl_bytes(result.stdout).strip()
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
