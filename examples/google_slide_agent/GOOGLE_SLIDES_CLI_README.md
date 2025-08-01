# Google Slides CLI Implementation

This directory contains scripts for running an interactive Google Slides agent with proper input prompt handling.

## Prerequisites

1. Python 3.7+ with required packages from `requirements.txt`
2. Google API credentials, set as environment variables:
   - `GOOGLE_CLIENT_ID`: Your Google Cloud OAuth 2.0 Client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google Cloud OAuth 2.0 Client Secret
   - `GOOGLE_REFRESH_TOKEN`: A valid refresh token for Google API access

## Getting Started

### Step 1: Start the Google Slides MCP WebSocket Server

First, start the WebSocket server that provides the Google Slides API tools:

```bash
python test_google_slides_mcp_script.py --transport websocket
```

This will start a WebSocket server on port 8765 that exposes Google Slides API operations.

### Step 2: Run one of the client scripts

#### Option 1: Simple Google Slides CLI (Recommended for Testing)

```bash
python simple_google_slides_cli.py --initial-prompt "Create a presentation titled 'My Test Presentation' using my email your.email@example.com"
```

This simplified script demonstrates XML tool format parsing and focuses only on the specific tool call scenario. It's the most reliable option for testing that the Google Slides integration works without the complexity of a full agent.

#### Option 2: Final Google Slides CLI (Full Agent Experience)

```bash
python final_google_slides_cli.py
```

This is the recommended script for interactive use. It implements a complete Google Slides agent with proper input prompt handling.

## Script Options

### 1. `simple_google_slides_cli.py`

```bash
usage: simple_google_slides_cli.py [-h] [--debug] [--initial-prompt INITIAL_PROMPT] [--llm-model LLM_MODEL]

Simple CLI for Google Slides operations

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging
  --initial-prompt INITIAL_PROMPT
                        Initial prompt to send to the LLM
  --llm-model LLM_MODEL
                        The LLM model to use
```

### 2. `final_google_slides_cli.py`

```bash
usage: final_google_slides_cli.py [-h] [--debug] [--initial-prompt INITIAL_PROMPT] [--llm-model LLM_MODEL]

Run an agent that interacts with Google Slides.

options:
  -h, --help            show this help message and exit
  --debug               Enable debug logging.
  --initial-prompt INITIAL_PROMPT
                        Initial prompt to send to the agent.
  --llm-model LLM_MODEL
                        The LLM model to use.
```

## Troubleshooting

- **WebSocket Connection Issues**: Make sure the WebSocket server is running before starting the client.
- **Google API Issues**: Check that your Google API credentials are correct and have the necessary scopes.
- **XML Format Issues**: If the LLM struggles to use the XML format, try using a lower temperature setting.

## Example Interactions

### Creating a Presentation

To create a new Google Slides presentation:

```
User: Create a presentation titled "Quarterly Business Review" for me using my email user@example.com
```

The LLM should respond using XML tool format like this:

```
<tool_code>
<command name="gslides_create_presentation">
    <arg name="title">Quarterly Business Review</arg>
    <arg name="user_google_email">user@example.com</arg>
</command>
</tool_code>
```

## The "You: " Prompt Issue

The original issue was that the standard `agent_cli.run()` function wasn't displaying the "You: " prompt correctly in some environments. This was because of how stdout/stderr streams were being handled and how input was being read.

## Solution Overview

The solution involves:

1. Directing all logging output to stderr instead of stdout
2. Using direct stdout writes with flush for interactive prompts
3. Using Python's `input()` function instead of `sys.stdin.readline()`
4. Managing agent events and synchronization directly

## Available Scripts

### 1. `final_google_slides_cli.py` (Recommended)

This is the recommended script to use. It implements a complete Google Slides agent with proper input prompt handling.

**Features:**
- Properly displays "You: " prompts
- Connects to Google Slides via MCP
- Supports tool approval workflow
- Handles streaming responses
- Clean error handling and resource cleanup

**Usage:**
```bash
python examples/final_google_slides_cli.py
```

**Options:**
- `--debug`: Enable debug logging
- `--initial-prompt`: Provide an initial prompt to the agent
- `--llm-model`: Specify the LLM model to use (default: GEMINI_2_0_FLASH_API)

### 2. `minimal_cli_test.py`

A minimal script that demonstrates the correct way to display the "You: " prompt without any agent functionality.

**Usage:**
```bash
python examples/minimal_cli_test.py
```

### 3. `direct_google_slides_cli.py`

An earlier implementation that also fixes the prompt issue but with a slightly different approach.

**Usage:**
```bash
python examples/direct_google_slides_cli.py
```

### 4. `run_google_slides_agent.py`

A more comprehensive implementation with additional features, similar to `run_poem_writer.py`.

**Usage:**
```bash
python examples/run_google_slides_agent.py
```

## Required Environment Variables

All scripts require the following environment variables:

- `TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH`: Path to the Google Slides MCP script
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GOOGLE_REFRESH_TOKEN`: Google OAuth refresh token

## Technical Details

### Why the Original Implementation Failed

The original implementation in `agent_cli.py` was using `sys.stdout.write()` and `sys.stdin.readline()` but had issues with:

1. Logging messages interfering with stdout prompts
2. Buffering issues where the prompt wasn't being displayed before waiting for input
3. Synchronization issues between the agent's event system and the CLI loop

### How the Fix Works

The key elements of the fix are:

1. **Separate stdout and stderr**: All logging goes to stderr, while interactive prompts go to stdout
2. **Explicit flushing**: Always flush stdout after writing prompts
3. **Direct input**: Use Python's built-in `input()` function which handles prompt display correctly
4. **Event synchronization**: Use asyncio events to properly coordinate between agent events and user input

## Troubleshooting

If you still don't see the "You: " prompt:

1. Make sure you're running in an interactive terminal
2. Check that your terminal supports ANSI escape sequences
3. Try running the `minimal_cli_test.py` script to verify basic prompt functionality
4. Ensure no other process is capturing or redirecting stdout 