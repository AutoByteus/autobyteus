"""
WSL + tmux backed terminal session implementation for Windows.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
from typing import Optional

from autobyteus.tools.terminal.wsl_utils import (
    ensure_wsl_available,
    ensure_wsl_distro_available,
    select_wsl_distro,
    windows_path_to_wsl,
)

logger = logging.getLogger(__name__)


class WslTmuxSession:
    """Terminal session backed by WSL + tmux (no pywinpty)."""

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._closed = False
        self._wsl_exe: Optional[str] = None
        self._distro: Optional[str] = None
        self._session_name: Optional[str] = None
        self._log_path: Optional[str] = None
        self._output_offset = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def is_alive(self) -> bool:
        return not self._closed

    async def start(self, cwd: str) -> None:
        if os.name != "nt":
            raise RuntimeError("WslTmuxSession is only supported on Windows.")
        if self._session_name is not None:
            raise RuntimeError("Session already started.")

        self._wsl_exe = ensure_wsl_available()
        ensure_wsl_distro_available(self._wsl_exe)
        self._distro = select_wsl_distro(self._wsl_exe)
        self._session_name = self._sanitize_session_name(self._session_id)

        await asyncio.to_thread(self._ensure_tmux_available)

        wsl_cwd = windows_path_to_wsl(cwd, wsl_exe=self._wsl_exe)
        await asyncio.to_thread(
            self._run_tmux,
            [
                "new-session",
                "-d",
                "-s",
                self._session_name,
                "-c",
                wsl_cwd,
                "-x",
                "120",
                "-y",
                "40",
                "/bin/bash",
                "--noprofile",
                "--norc",
                "-i",
            ],
        )
        await asyncio.to_thread(
            self._run_tmux,
            ["send-keys", "-t", self._session_name, "export PS1='$ '", "C-m"],
        )
        self._log_path = f"/tmp/autobyteus_tmux_{self._session_name}.log"
        await asyncio.to_thread(self._reset_log)
        await asyncio.to_thread(self._start_pipe)

        logger.info(
            "Started WSL tmux session %s in %s (distro=%s)",
            self._session_name,
            wsl_cwd,
            self._distro,
        )

    async def write(self, data: bytes) -> None:
        if self._closed:
            raise RuntimeError("Session is closed")
        if self._session_name is None:
            raise RuntimeError("Session not started")

        text = data.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        parts = text.split("\n")
        for idx, part in enumerate(parts):
            if part:
                await asyncio.to_thread(
                    self._run_tmux,
                    ["send-keys", "-t", self._session_name, "-l", part],
                )
            if idx < len(parts) - 1:
                await asyncio.to_thread(
                    self._run_tmux,
                    ["send-keys", "-t", self._session_name, "C-m"],
                )

    async def read(self, timeout: float = 0.1) -> Optional[bytes]:
        if self._closed or self._session_name is None:
            return None
        data = await asyncio.to_thread(self._read_log_delta)
        if not data:
            if timeout:
                await asyncio.sleep(timeout)
            return None
        return data

    def resize(self, rows: int, cols: int) -> None:
        if self._closed or self._session_name is None:
            return
        rows = max(1, int(rows))
        cols = max(1, int(cols))
        try:
            self._run_tmux(
                ["resize-window", "-t", self._session_name, "-x", str(cols), "-y", str(rows)]
            )
        except Exception as exc:
            logger.debug("Failed to resize tmux session %s: %s", self._session_name, exc)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._session_name:
            try:
                await asyncio.to_thread(self._stop_pipe)
                await asyncio.to_thread(
                    self._run_tmux, ["kill-session", "-t", self._session_name]
                )
            except Exception:
                pass
        self._session_name = None
        self._log_path = None
        self._output_offset = 0
        logger.info("Closed WSL tmux session %s", self._session_id)

    def _ensure_tmux_available(self) -> None:
        try:
            self._run_wsl_command(["tmux", "-V"], check=True)
        except RuntimeError as exc:
            raise RuntimeError(
                "tmux is required in the WSL distro. Install with `sudo apt install tmux`."
            ) from exc

    def _run_tmux(self, args: list[str]) -> subprocess.CompletedProcess:
        return self._run_wsl_command(["tmux", *args], check=True)

    def _reset_log(self) -> None:
        if not self._log_path:
            return
        self._run_wsl_command(["sh", "-c", f"rm -f {self._log_path}; : > {self._log_path}"], check=True)
        self._output_offset = 0

    def _start_pipe(self) -> None:
        if not self._log_path:
            return
        cmd = f"tmux pipe-pane -o -t {self._session_name}:0.0 'cat >> {self._log_path}'"
        self._run_wsl_command(["sh", "-c", cmd], check=True)

    def _stop_pipe(self) -> None:
        if not self._session_name:
            return
        self._run_tmux(["pipe-pane", "-t", f"{self._session_name}:0.0"])

    def _read_log_delta(self) -> bytes:
        if not self._log_path:
            return b""
        cmd = (
            f"if [ -f {self._log_path} ]; then "
            f"dd if={self._log_path} bs=1 skip={self._output_offset} 2>/dev/null; "
            f"fi"
        )
        result = self._run_wsl_command(["sh", "-c", cmd], check=True)
        data = result.stdout or b""
        self._output_offset += len(data)
        return data

    def _run_wsl_command(self, args: list[str], check: bool) -> subprocess.CompletedProcess:
        if not self._wsl_exe or not self._distro:
            raise RuntimeError("WSL session not initialized.")
        cmd = [self._wsl_exe, "-d", self._distro, "--exec", *args]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=False,
            check=False,
            timeout=10,
        )
        if check and result.returncode != 0:
            stderr = self._decode_output(result.stderr)
            raise RuntimeError(stderr or "WSL command failed")
        return result

    @staticmethod
    def _decode_output(raw: bytes) -> str:
        if not raw:
            return ""
        if b"\x00" in raw:
            return raw.decode("utf-16-le", errors="replace")
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _sanitize_session_name(session_id: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)
        return f"autobyteus_{base}"
