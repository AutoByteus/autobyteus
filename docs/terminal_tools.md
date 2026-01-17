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

### Windows-Specific Testing

**Important**: On Windows, the standard integration tests will fail with `No module named 'fcntl'` because `fcntl` is a Unix-only module used by `PtySession`.

Use the dedicated Windows test file instead:

```bash
# Run Windows-specific WSL tests
uv run python -m pytest tests/unit_tests/tools/terminal/test_wsl_terminal_windows.py -v

# Or use the windows marker
uv run python -m pytest -v -m "windows"
```

The Windows tests:

- Only import WSL-related modules (no Unix dependencies)
- Verify WSL executable and distro availability
- Test real bash command execution inside WSL
- Validate state persistence and background processes

**Prerequisites**:

- WSL installed and configured (see Windows Setup Guide below)
- Ubuntu or another Linux distro installed in WSL
- `tmux` installed inside the WSL distro (`sudo apt install tmux`)

## Platform Support

- **Linux/macOS**: Full support out of the box.
- **Windows**: Supported via **WSL (Windows Subsystem for Linux)**.

### 🪟 Windows Setup Guide (Required for `run_bash`)

On Windows, the `run_bash` tool executes commands inside a real Linux environment running via WSL. Follow these steps to set it up:

#### 1. Install WSL

Open PowerShell as **Administrator** and run:

```powershell
wsl --install
```

- **Restart your computer** when prompted.
- After restarting, a window will open to finish installing Ubuntu (or the default distro).
- Create a **username** and **password** when asked (remember these!).

#### 2. Set Ubuntu as the default WSL distro

If you have multiple distros (for example, Docker's minimal distro), set Ubuntu
as the default so tools run against a full Linux environment:

```powershell
wsl -l -v
wsl --set-default Ubuntu
```

#### 3. Install Python 3.11 (Required)

Inside your new WSL terminal (Ubuntu), run these commands to install Python 3.11:

```bash
# Update package lists
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y software-properties-common curl git unzip build-essential

# Add Python PPA (if needed for older Ubuntu versions)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

#### 4. Install Node.js & npm (Recommended)

Most web development agents will need Node.js. Install the latest LTS version:

```bash
# Install Node Version Manager (nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Close and reopen your terminal, or source the profile
source ~/.bashrc

# Install Node.js LTS
nvm install --lts

# Verify installation
node --version
npm --version
```

#### 5. Install tmux (Required)

The Windows terminal backend uses tmux inside WSL:

```bash
sudo apt install -y tmux
tmux -V
```

#### 6. Accessing your Windows Files (Automatic)

WSL automatically "mounts" your Windows drives. You can access your Windows folders using the path `/mnt/<drive-letter>/`.

- **Your C: Drive**: Accessible at `/mnt/c/`
- **Your Projects**: If your code is in `C:\Code\my-project`, the agent can access it via:
  ```bash
  cd /mnt/c/Code/my-project
  ```

This allows Autobyteus agents to manage your Windows folders seamlessly using Linux tools.

#### 7. GUI Support (Optional)

Modern WSL supports graphical applications. If you install a Linux app inside Ubuntu, it will automatically appear in your **Windows Start Menu**.

For easier file management, you can install a Linux file manager:

```bash
sudo apt install nautilus -y
```

Then, just search for **"Nautilus"** in your Windows Start Menu to browse your WSL and Windows files graphically.

#### 8. How it works

When an agent runs `run_bash("npm install")`:

1.  Autobyteus (running on Windows) talks to WSL and uses `tmux` for the shell session.
2.  The command executes inside your WSL Ubuntu instance.
3.  Files created (like `node_modules`) live in the WSL file system, or on your Windows drive if you `cd` there first.
