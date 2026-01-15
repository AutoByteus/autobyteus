# Terminal Tools

PTY-based terminal tools providing stateful command execution and background process management for agents.

## Overview

These tools replace the legacy `bash_executor` with a PTY-based implementation where:

- **State persists** — `cd` and environment variables persist across commands
- **Background processes** — Start servers, check output, stop them

## Tools

### `run_bash`

Execute a command in a stateful terminal session.

```python
await run_bash(context, command="npm install", timeout_seconds=120)
```

**Parameters:**

- `command` (str): Bash command to execute
- `timeout_seconds` (int): Maximum wait time (default: 30)

**Returns:** `TerminalResult` with `stdout`, `stderr`, `exit_code`, `timed_out`

**Key behavior:**

- State persists between calls (`cd`, `export` work as expected)
- Command is killed if timeout exceeded

---

### `start_background_process`

Start a long-running process (server, watcher) in the background.

```python
result = await start_background_process(context, command="yarn dev")
# result: {"process_id": "bg_001", "status": "started"}
```

**Parameters:**

- `command` (str): Command to run

**Returns:** dict with `process_id` and `status`

---

### `get_process_output`

Read recent output from a background process.

```python
result = await get_process_output(context, process_id="bg_001", lines=50)
# result: {"output": "...", "is_running": True, "process_id": "bg_001"}
```

**Parameters:**

- `process_id` (str): ID from `start_background_process`
- `lines` (int): Number of lines to return (default: 100)

---

### `stop_background_process`

Stop a background process.

```python
result = await stop_background_process(context, process_id="bg_001")
# result: {"status": "stopped", "process_id": "bg_001"}
```

## Architecture

```
autobyteus/tools/terminal/
├── types.py                   # TerminalResult, ProcessInfo dataclasses
├── output_buffer.py           # Ring buffer for output (bounded memory)
├── prompt_detector.py         # Detects when commands complete
├── pty_session.py             # Low-level PTY wrapper (fork/exec)
├── terminal_session_manager.py # Main stateful terminal
├── background_process_manager.py # Background process lifecycle
└── tools/                     # LLM-facing tool functions
```

## Testing

Run all terminal tests:

```bash
uv run python -m pytest tests/unit_tests/tools/terminal/ -v
```

Run integration tests only (spawn real PTY):

```bash
uv run python -m pytest tests/unit_tests/tools/terminal/ -v -m "integration"
```

## Platform Support

- **Linux/macOS**: Full support via PTY
- **Windows**: Supported via WSL + ConPTY (requires WSL installed and `pywinpty`)
  - Install WSL: `wsl --install` (then reboot and install a distro)
  - Ensure tools (python/node) are installed inside WSL if you want bash commands to work
