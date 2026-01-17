# WSL + tmux Terminal Backend (Windows)

## Context

The current Windows terminal backend uses `pywinpty` (ConPTY). It is unstable
and difficult to bundle in one-file builds. We want a Windows backend that is
stable, explicit, and avoids `pywinpty` entirely.

## Goals

- Replace the Windows PTY backend with a WSL + `tmux` implementation.
- Keep the WebSocket protocol unchanged.
- Maintain parity with the current terminal session interface.
- Provide clear error messages when WSL or tmux is unavailable.

## Non-goals

- Changing frontend protocol or UI.
- Replacing the terminal WebSocket handler.
- Adding new terminal features.

## Proposed Design

### 1) New Session Class: `WslTmuxSession`

Add `autobyteus/tools/terminal/wsl_tmux_session.py` implementing:

```
start(cwd: str) -> None
write(data: bytes) -> None
read(timeout: float = 0.1) -> Optional[bytes]
resize(rows: int, cols: int) -> None
close() -> None
```

The class uses `wsl.exe` + `tmux` for all terminal I/O.

### 2) tmux Lifecycle

Each terminal session maps to a tmux session:

- name: `autobyteus_<session_id>`
- window: `0`

Startup sequence:

1) Ensure WSL is available and a distro exists.
2) Ensure `tmux` is installed in the selected distro.
3) Create session:
   `tmux new-session -d -s <name> -c <cwd> /bin/bash`
4) Simplify prompt:
   `tmux send-keys -t <name> 'export PS1="$ "' C-m`
5) Prime output offset so the first `read()` does not replay prompt noise.

### 3) Output Streaming

Terminal output is fetched from tmux panes:

- Use `tmux capture-pane -pt <name> -S -2000 -E -1` to read recent output.
- Track `last_line_index` and `last_col_index`.
- Return only new output since the last read.

This keeps the polling loop in `TerminalHandler` working unchanged.

### 4) Resize

Resize is forwarded to tmux:

`tmux resize-window -t <name> -x <cols> -y <rows>`

### 5) Backend Selection

Update `autobyteus/tools/terminal/session_factory.py`:

- On Windows, always return `WslTmuxSession`.
- Remove `WslPtySession` (legacy).

If you want a soft rollout, use a feature flag:

- `AUTOBYTEUS_USE_WSL_TMUX=1` -> `WslTmuxSession`
- else -> legacy (temporary)

### 6) Error Handling

Raise clear errors on:

- `wsl.exe` not found
- no WSL distro installed
- `tmux` missing in distro

These should propagate to the server logs and the WebSocket close code `1011`.

## Dependencies

Windows requires:

- WSL installed with at least one distro.
- `tmux` installed inside the distro (e.g., `sudo apt install tmux`).

No `pywinpty` dependency is required.

## Tests

### Unit Tests (autobyteus)

- Validate tmux command construction.
- Validate output delta extraction.
- Validate error cases with mocked subprocess calls.

### Integration Tests (autobyteus-server)

- WebSocket connect + input + output echo using the tmux backend.
- Skip if WSL or tmux is unavailable.

## Migration Plan

1) Implement `WslTmuxSession`.
2) Update `session_factory` to select it on Windows.
3) Remove `WslPtySession` and `pywinpty` dependency.
4) Add unit + integration tests.
5) Update docs and build guidance.
