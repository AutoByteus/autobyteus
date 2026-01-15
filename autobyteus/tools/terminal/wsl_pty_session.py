"""
WSL-backed PTY session implementation for Windows.
"""

import asyncio
import logging
import os
import shlex
from typing import Optional

from autobyteus.tools.terminal.wsl_utils import (
    ensure_wsl_available,
    ensure_wsl_distro_available,
    windows_path_to_wsl,
)

logger = logging.getLogger(__name__)


class WslPtySession:
    """PTY-like session backed by WSL + ConPTY (via pywinpty)."""

    def __init__(self, session_id: str):
        self._session_id = session_id
        self._process = None
        self._closed = False
        self._cwd: Optional[str] = None
        self._wsl_exe: Optional[str] = None

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def is_alive(self) -> bool:
        if self._process is None or self._closed:
            return False
        isalive = getattr(self._process, "isalive", None)
        if callable(isalive):
            return bool(isalive())
        return True

    async def start(self, cwd: str) -> None:
        if self._process is not None:
            raise RuntimeError("Session already started")
        if os.name != "nt":
            raise RuntimeError("WslPtySession is only supported on Windows.")

        self._cwd = cwd
        self._wsl_exe = ensure_wsl_available()
        ensure_wsl_distro_available(self._wsl_exe)

        try:
            from pywinpty import PtyProcess
        except ImportError as exc:
            raise RuntimeError(
                "pywinpty is required for Windows PTY support. "
                "Install with `pip install pywinpty`."
            ) from exc

        command = f"{self._wsl_exe} --exec bash --noprofile --norc -i"
        self._process = PtyProcess.spawn(command)

        await asyncio.sleep(0.1)

        wsl_cwd = windows_path_to_wsl(cwd, wsl_exe=self._wsl_exe)
        await self._write_command("export TERM=xterm-256color")
        await self._write_command("export PS1='\\w $ '")
        await self._write_command(f"cd {shlex.quote(wsl_cwd)}")

        logger.info("Started WSL PTY session %s in %s", self._session_id, wsl_cwd)

    async def _write_command(self, command: str) -> None:
        if not command.endswith("\n"):
            command += "\n"
        await self.write(command.encode("utf-8"))

    async def write(self, data: bytes) -> None:
        if self._closed:
            raise RuntimeError("Session is closed")
        if self._process is None:
            raise RuntimeError("Session not started")

        text = data.decode("utf-8", errors="replace")
        await asyncio.to_thread(self._process.write, text)

    async def read(self, timeout: float = 0.1) -> Optional[bytes]:
        if self._closed:
            return None
        if self._process is None:
            raise RuntimeError("Session not started")

        def _read_chunk():
            try:
                return self._process.read(4096)
            except Exception:
                return ""

        try:
            chunk = await asyncio.wait_for(
                asyncio.to_thread(_read_chunk),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None

        if not chunk:
            return None

        if isinstance(chunk, bytes):
            return chunk

        return str(chunk).encode("utf-8", errors="replace")

    def resize(self, rows: int, cols: int) -> None:
        if self._process is None or self._closed:
            return

        try:
            resize_fn = getattr(self._process, "setwinsize", None)
            if callable(resize_fn):
                resize_fn(rows, cols)
        except Exception as exc:
            logger.debug("Failed to resize WSL PTY: %s", exc)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

        if self._process is not None:
            try:
                await asyncio.to_thread(self._process.close)
            except Exception:
                pass
            self._process = None

        logger.info("Closed WSL PTY session %s", self._session_id)
