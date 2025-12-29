# Autobyteus

Autobyteus is an open-source, application-first agentic framework for Python. It is designed to help developers build, test, and deploy complex, stateful, and extensible AI agents by providing a robust architecture and a powerful set of tools.

![Autobyteus TUI Dashboard](docs/images/image_1.png)

## Architecture

Autobyteus is built with a modular, event-driven architecture designed for extensibility and clear separation of concerns. The key components are:

-   **Agent Core**: The heart of the system. Each agent is a stateful, autonomous entity that runs as a background process in its own thread, managed by a dedicated `AgentWorker`. This design makes every agent a truly independent entity capable of handling long-running tasks.
-   **Agent Teams**: The framework provides powerful constructs for building hierarchical multi-agent systems. The `AgentTeam` module allows you to compose teams of individual agents and even nest teams within other teams, enabling sophisticated, real-world organizational structures and delegation patterns.
-   **Context & Configuration**: Agent behavior is defined through a static configuration (`AgentConfig`) and its dynamic state is managed in `AgentRuntimeState`. These are bundled into a comprehensive `AgentContext` that is passed to all components, providing a single source of truth.
-   **Event-Driven System**: Agents operate on an internal `asyncio` event loop. User messages, tool results, and internal signals are handled as events, which are processed by dedicated `EventHandlers`. This decouples logic and makes the system highly extensible.
-   **Pluggable Processors & Hooks**: The framework provides a chain of extension points to inject custom logic at every major step of an agent's reasoning loop. This architecture powers features like flexible tool format parsing. You can customize behavior by implementing:
    -   **`InputProcessors`**: To modify or enrich user messages *before* they are sent to the LLM.
    -   **`LLMResponseProcessors`**: To parse the LLM's raw output and extract structured actions, such as tool calls.
    -   **`ToolExecutionResultProcessors` (Tool Result Processors)**: To modify the result from a tool *before* it is sent back to the LLM for the next step of reasoning (e.g., formatting, summarization, artifact extraction).
    -   **Lifecycle Event Processors**: To run custom code on specific lifecycle events (e.g., `BEFORE_LLM_CALL`, `AFTER_TOOL_EXECUTE`).
-   **Context-Aware Tooling**: Tools are first-class citizens that receive the agent's full `AgentContext` during execution. This allows tools to be deeply integrated with the agent's state, configuration, and workspace, enabling more intelligent and powerful actions.
-   **Tool Approval Flow**: The framework has native support for human-in-the-loop workflows. By setting `auto_execute_tools=False` in the agent's configuration, the agent will pause before executing a tool, emit an event requesting permission, and wait for external approval before proceeding.
-   **MCP Integration**: The framework has native support for the Model Context Protocol (MCP). This allows agents to discover and use tools from external, language-agnostic tool servers, making the ecosystem extremely flexible and ready for enterprise integration.
-   **Agent Skills**: A powerful mechanism for extending agent capabilities using modular, file-based skills. Each skill is a directory containing a map (`SKILL.md`) and arbitrary assets (code, docs, templates). Skills can be preloaded or dynamically fetched via the `load_skill` tool, enabling human-like, just-in-time retrieval without bloating the context window.

## Key Features

#### Interactive TUI Dashboard
Launch and monitor your agent teams with our built-in Textual-based TUI.
-   **Hierarchical View**: See the structure of your team, including sub-teams and their agents.
-   **Real-Time Status**: Agent and team statuses are updated live, showing you who is idle, thinking, or executing a tool.
-   **Detailed Logs**: Select any agent to view a detailed, streaming log of their thoughts, actions, and tool interactions.
-   **Live Task Plan**: Watch your team's `TaskPlan` update in real-time as the coordinator publishes a plan and agents complete their tasks.

| TUI - Detailed Agent Log | TUI - Task Plan with Completed Task |
| :---: | :---: |
| ![Autobyteus Agent Log](docs/images/image_4.png) | ![Autobyteus Task Plan](docs/images/image_3.png) |

#### Fluent Team Building
Define complex agent and team structures with an intuitive, fluent API. The `AgentTeamBuilder` makes composing your team simple and readable.

```python
# --- From the Multi-Researcher Team Example ---
research_team = (
    AgentTeamBuilder(
        name="MultiSpecialistResearchTeam",
        description="A team for delegating to multiple specialists."
    )
    .set_coordinator(coordinator_config)
    .add_agent_node(researcher_web_config)
    .add_agent_node(researcher_db_config)
    .build()
)
```

#### Flexible Tool Formatting (JSON & XML)
Autobyteus intelligently handles tool communication with LLMs while giving you full control.
-   **Provider-Aware by Default**: The framework automatically generates tool manifests and parses responses in the optimal format for the selected LLM provider (e.g., JSON for OpenAI/Gemini, XML for Anthropic).
-   **XML Override for Efficiency**: You can set `use_xml_tool_format=True` on an `AgentConfig` or `AgentTeamBuilder` to force the use of XML for tool calls, which can be more efficient and reliable than JSON for complex tool schemas.

#### Flexible Communication Protocols
Choose the collaboration pattern that best fits your use case with configurable `TaskNotificationMode`s.
-   **`AGENT_MANUAL_NOTIFICATION` (Default)**: A traditional approach where a coordinator agent is responsible for creating a plan and then explicitly notifying other agents to begin their work via messages.
-   **`SYSTEM_EVENT_DRIVEN`**: A more automated approach where the coordinator's only job is to publish a plan to the `TaskPlan`. The framework then monitors the board and automatically notifies agents when their tasks become unblocked, enabling parallel execution and reducing coordinator overhead.

## Requirements

-   **Python Version**: Python 3.11.x is the supported version for this project (>=3.11,<3.12). Using other versions may cause dependency conflicts.

## Getting Started

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/autobyteus.git
    cd autobyteus
    ```

2.  **Create a local `uv` environment (recommended):**
    ```bash
    uv venv .venv --python 3.11
    ```

3.  **Install dependencies:**
    - **For users:**
      ```bash
      uv sync
      ```
    - **For developers:**
      ```bash
      uv sync --extra dev
      ```

4.  **Set up Environment Variables:**
    Create a `.env` file in the root of the project and add your LLM provider API keys:
    ```
    # .env
    OPENAI_API_KEY="sk-..."
    KIMI_API_KEY="your-kimi-api-key"
    # etc.
    ```

### Running the Examples

The best way to experience Autobyteus is to run one of the included examples. The event-driven software engineering team is a great showcase of the framework's capabilities.

```bash
# Run the event-driven software engineering team example
python autobyteus/examples/agent_team/event_driven/run_software_engineering_team.py --llm-model gpt-4o

# Run the hierarchical debate team example
python autobyteus/examples/agent_team/manual_notification/run_debate_team.py --llm-model gpt-4-turbo

# Run the hierarchical skills example (modular, file-based capabilities)
python examples/run_agent_with_skill.py --llm-model gpt-4o
```
You can see all available models and their identifiers by running an example with the `--help-models` flag.

## Testing

### Streamable HTTP MCP integration

Some integration tests rely on the toy streamable MCP server that lives in
`autobyteus_mcps/streamable_http_mcp_toy`. Start it in a separate terminal
before running the test, for example:

```bash
cd autobyteus_mcps/streamable_http_mcp_toy
python src/streamable_http_mcp_toy/server.py --host 127.0.0.1 --port 8764
```

With the server running, execute the HTTP transport test:

```bash
uv run python -m pytest tests/integration_tests/tools/mcp/test_http_managed_server_integration.py
```

If you bind the server elsewhere, set `STREAMABLE_HTTP_MCP_URL` to the full
`http://` or `https://` endpoint before running pytest so the test can find it.

### Secure WebSocket (WSS) MCP integration

The toy WebSocket MCP server lives in `autobyteus_mcps/wss_mcp_toy`. It exposes
the same diagnostic tools as the HTTP toy server but requires TLS and an Origin
header. To exercise the WebSocket transport:

1. In a separate terminal start the toy server:

   ```bash
   cd autobyteus_mcps/wss_mcp_toy
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ./scripts/generate-dev-cert.sh  # creates certs/dev-cert.pem + certs/dev-key.pem
   wss-mcp-toy --cert certs/dev-cert.pem --key certs/dev-key.pem --host 127.0.0.1 --port 8765 --allowed-origin https://localhost
   ```

2. Run the WebSocket transport test (defaults assume the process above is
   listening on `wss://127.0.0.1:8765/mcp`):

   ```bash
   uv run python -m pytest tests/integration_tests/tools/mcp/test_websocket_managed_server_integration.py
   ```

Customize the target URL or TLS behavior via environment variables when
running pytest:

- `WSS_MCP_URL` – full `ws://` or `wss://` endpoint (default `wss://127.0.0.1:8765/mcp`).
- `WSS_MCP_ORIGIN` – Origin header value (default `https://localhost`).
- `WSS_MCP_VERIFY_TLS` – set to `true`/`1` to enforce TLS verification
  (default `false` for the self-signed dev cert).
- `WSS_MCP_CA_FILE`, `WSS_MCP_CLIENT_CERT`, `WSS_MCP_CLIENT_KEY` – optional
  paths if you want to trust a custom CA or present a client certificate.

### Building the Library

To build Autobyteus as a distributable package, follow these steps:

1.  Ensure dev dependencies are installed:
    ```bash
    uv sync --extra dev
    ```

2.  Build the distribution packages defined in `pyproject.toml`:
    ```
    uv run python -m build
    ```

This will create a `dist` directory containing the `sdist` and `wheel` artifacts.

## Contributing

(Add guidelines for contributing to the project)

## License

This project is licensed under the MIT License.
