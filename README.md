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
    -   **`ToolExecutionResultProcessors`**: To modify the result from a tool *before* it is sent back to the LLM for the next step of reasoning.
    -   **`PhaseHooks`**: To run custom code on specific agent lifecycle transitions (e.g., when an agent becomes `IDLE`).
-   **Context-Aware Tooling**: Tools are first-class citizens that receive the agent's full `AgentContext` during execution. This allows tools to be deeply integrated with the agent's state, configuration, and workspace, enabling more intelligent and powerful actions.
-   **Tool Approval Flow**: The framework has native support for human-in-the-loop workflows. By setting `auto_execute_tools=False` in the agent's configuration, the agent will pause before executing a tool, emit an event requesting permission, and wait for external approval before proceeding.
-   **MCP Integration**: The framework has native support for the Model Context Protocol (MCP). This allows agents to discover and use tools from external, language-agnostic tool servers, making the ecosystem extremely flexible and ready for enterprise integration.

## Key Features

#### 📊 Interactive TUI Dashboard
Launch and monitor your agent teams with our built-in Textual-based TUI.
-   **Hierarchical View**: See the structure of your team, including sub-teams and their agents.
-   **Real-Time Status**: Agent and team statuses are updated live, showing you who is idle, thinking, or executing a tool.
-   **Detailed Logs**: Select any agent to view a detailed, streaming log of their thoughts, actions, and tool interactions.
-   **Live Task Board**: Watch your team's `TaskBoard` update in real-time as the coordinator publishes a plan and agents complete their tasks.

| TUI - Detailed Agent Log | TUI - Task Board with Completed Task |
| :---: | :---: |
| ![Autobyteus Agent Log](docs/images/image_4.png) | ![Autobyteus Task Board](docs/images/image_3.png) |

#### 🏗️ Fluent Team Building
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

#### 🔁 Flexible Tool Formatting (JSON & XML)
Autobyteus intelligently handles tool communication with LLMs while giving you full control.
-   **Provider-Aware by Default**: The framework automatically generates tool manifests and parses responses in the optimal format for the selected LLM provider (e.g., JSON for OpenAI/Gemini, XML for Anthropic).
-   **XML Override for Efficiency**: You can set `use_xml_tool_format=True` on an `AgentConfig` or `AgentTeamBuilder` to force the use of XML for tool calls, which can be more efficient and reliable than JSON for complex tool schemas.

#### 📈 Flexible Communication Protocols
Choose the collaboration pattern that best fits your use case with configurable `TaskNotificationMode`s.
-   **`AGENT_MANUAL_NOTIFICATION` (Default)**: A traditional approach where a coordinator agent is responsible for creating a plan and then explicitly notifying other agents to begin their work via messages.
-   **`SYSTEM_EVENT_DRIVEN`**: A more automated approach where the coordinator's only job is to publish a plan to the `TaskBoard`. The framework then monitors the board and automatically notifies agents when their tasks become unblocked, enabling parallel execution and reducing coordinator overhead.

## Requirements

-   **Python Version**: Python 3.11 is the recommended and tested version for this project. Using newer versions of Python may result in dependency conflicts when installing the required packages. For a stable and tested environment, please use Python 3.11.

## Getting Started

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/autobyteus.git
    cd autobyteus
    ```

2.  **For users:**
    To install Autobyteus and its core dependencies:
    ```bash
    pip install .
    ```

3.  **For developers:**
    To install Autobyteus with all development and example dependencies (including the TUI):
    ```bash
    pip install -r requirements-dev.txt
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
```
You can see all available models and their identifiers by running an example with the `--help-models` flag.

### Building the Library

To build Autobyteus as a distributable package, follow these steps:

1.  Ensure you have the latest version of `setuptools` and `wheel` installed:
    ```
    pip install --upgrade setuptools wheel
    ```

2.  Build the distribution packages:
    ```
    python setup.py sdist bdist_wheel
    ```

This will create a `dist` directory containing the built `sdist` and `wheel` distributions.

## Contributing

(Add guidelines for contributing to the project)

## License

This project is licensed under the MIT License.
