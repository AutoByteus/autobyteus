"""
WSL-backed PTY session implementation for Windows.
"""

import asyncio
import logging
import os
import shlex
import threading
import time
from typing import Optional

from autobyteus.tools.terminal.wsl_utils import (
    ensure_wsl_available,
    ensure_wsl_distro_available,
    select_wsl_distro,
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
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._read_queue: Optional[asyncio.Queue] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_stop = threading.Event()

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
            from winpty import PtyProcess
        except ImportError as exc:
            raise RuntimeError(
                "pywinpty is required for Windows PTY support. "
                "Install with `pip install pywinpty`."
            ) from exc

        distro = select_wsl_distro(self._wsl_exe)

        def _quote_arg(arg: str) -> str:
            if " " in arg:
                return f"\"{arg}\""
            return arg

        wsl_exe = _quote_arg(self._wsl_exe)
        distro_arg = _quote_arg(distro)
        command = f"{wsl_exe} -d {distro_arg} --exec bash --noprofile --norc -i"
        self._process = PtyProcess.spawn(command)

        await asyncio.sleep(0.1)
        self._loop = asyncio.get_running_loop()
        self._read_queue = asyncio.Queue()
        self._reader_stop.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            name=f"wsl-pty-reader-{self._session_id}",
            daemon=True,
        )
        self._reader_thread.start()
        await self._await_shell_ready()

        wsl_cwd = windows_path_to_wsl(cwd, wsl_exe=self._wsl_exe)
        await self._write_command("export TERM=dumb")
        await self._write_command("export PS1='$ '")
        await self._write_command(f"cd {shlex.quote(wsl_cwd)}")
        await self._drain_output(timeout=0.5)
        await self._await_shell_ready(timeout=2.0)

        logger.info(
            "Started WSL PTY session %s in %s (distro=%s)",
            self._session_id,
            wsl_cwd,
            distro,
        )

    async def _write_command(self, command: str) -> None:
        if not command.endswith("\n"):
            command += "\n"
        await self.write(command.encode("utf-8"))

    async def _await_shell_ready(self, timeout: float = 3.0) -> None:
        """Wait briefly for the WSL shell to become responsive."""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        output = b""

        while loop.time() < deadline:
            data = await self.read(timeout=0.1)
            if data:
                output += data
                if b"$ " in output or b"# " in output:
                    return
            else:
                await asyncio.sleep(0.05)

    async def _drain_output(self, timeout: float = 0.5) -> None:
        """Drain any pending output after init commands."""
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            data = await self.read(timeout=0.05)
            if not data:
                await asyncio.sleep(0.05)

    async def write(self, data: bytes) -> None:
        if self._closed:
            raise RuntimeError("Session is closed")
        if self._process is None:
            raise RuntimeError("Session not started")

        text = data.decode("utf-8", errors="replace")
        if "\n" in text:
            # WinPTY expects CRLF for command submission on Windows.
            text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        await asyncio.to_thread(self._process.write, text)
        flush = getattr(self._process, "flush", None)
        if callable(flush):
            await asyncio.to_thread(flush)

    async def read(self, timeout: float = 0.1) -> Optional[bytes]:
        if self._closed:
            return None
        if self._process is None:
            raise RuntimeError("Session not started")
        if self._read_queue is None:
            return None

        try:
            chunk = await asyncio.wait_for(self._read_queue.get(), timeout=timeout)
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
        self._reader_stop.set()

        if self._process is not None:
            try:
                await asyncio.to_thread(self._process.close)
            except Exception:
                pass
            self._process = None
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None
        self._read_queue = None
        self._loop = None

        logger.info("Closed WSL PTY session %s", self._session_id)

    def _reader_loop(self) -> None:
        while not self._reader_stop.is_set() and self._process is not None:
            try:
                data = self._process.read(4096)
            except Exception as exc:
                if self._reader_stop.is_set():
                    break
                logger.debug("WSL PTY reader error: %s", exc)
                time.sleep(0.05)
                continue
            if not data:
                continue
            if self._loop is not None and self._read_queue is not None:
                try:
                    self._loop.call_soon_threadsafe(self._read_queue.put_nowait, data)
                except RuntimeError:
                    # Event loop closed; stop reader to avoid unhandled thread errors.
                    break
