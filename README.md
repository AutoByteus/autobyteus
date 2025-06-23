# Autobyteus

Autobyteus is an open-source, application-first agentic framework for Python. It is designed to help developers build, test, and deploy complex, stateful, and extensible AI agents by providing a robust architecture and a powerful set of tools.

## Architecture

Autobyteus is built with a modular, event-driven architecture designed for extensibility and clear separation of concerns. The key components are:

-   **Agent Core**: The heart of the system. Each agent is a stateful, autonomous entity that runs as a background process in its own thread, managed by a dedicated `AgentWorker`. This design makes every agent a truly independent entity capable of handling long-running tasks.
-   **Context & Configuration**: Agent behavior is defined through a static configuration (`AgentConfig`) and its dynamic state is managed in `AgentRuntimeState`. These are bundled into a comprehensive `AgentContext` that is passed to all components, providing a single source of truth.
-   **Event-Driven System**: Agents operate on an internal `asyncio` event loop. User messages, tool results, and internal signals are handled as events, which are processed by dedicated `EventHandlers`. This decouples logic and makes the system highly extensible.
-   **Pluggable Processors & Hooks**: The framework provides extension points to inject custom logic. `InputProcessors` and `LLMResponseProcessors` modify data in the main processing pipeline, while `PhaseHooks` allow custom code to run on specific agent lifecycle transitions (e.g., from `BOOTSTRAPPING` to `IDLE`).
-   **Context-Aware Tooling**: Tools are first-class citizens that receive the agent's full `AgentContext` during execution. This allows tools to be deeply integrated with the agent's state, configuration, and workspace, enabling more intelligent and powerful actions.
-   **Tool Approval Flow**: The framework has native support for human-in-the-loop workflows. By setting `auto_execute_tools=False` in the agent's configuration, the agent will pause before executing a tool, emit an event requesting permission, and wait for external approval before proceeding.
-   **MCP Integration**: The framework has native support for the Model Context Protocol (MCP). This allows agents to discover and use tools from external, language-agnostic tool servers, making the ecosystem extremely flexible and ready for enterprise integration.

## Features

- **Context-Aware Workflows**: Each step in the development process interacts with large language models to provide relevant assistance.
- **Lifecycle Integration**: Supports the entire software development lifecycle, starting from requirement engineering.
- **Memory Management**: Custom memory management system supporting different memory providers and embeddings.

## Knowledge Base

A significant part of Autobyteus is our custom-designed knowledge base focused on software and application development. The knowledge base is structured to support the entire development process, with particular emphasis on requirement engineering, which is crucial for successful project outcomes.

## Requirements

-   **Python Version**: Python 3.11 is the recommended and tested version for this project. Using newer versions of Python may result in dependency conflicts when installing the required packages. For a stable and tested environment, please use Python 3.11.

## Getting Started

### Installation

1. **For users:**
   To install Autobyteus, run:
   ```
   pip install .
   ```

2. **For developers:**
   To install Autobyteus with development dependencies, run:
   ```
   pip install -r requirements-dev.txt
   ```

3. **Platform-specific dependencies:**
   To install platform-specific dependencies, run:
   ```
   python setup.py install_platform_deps
   ```

### Building the Library

To build Autobyteus as a distributable package, follow these steps:

1. Ensure you have the latest version of `setuptools` and `wheel` installed:
   ```
   pip install --upgrade setuptools wheel
   ```

2. Build the distribution packages:
   ```
   python setup.py sdist bdist_wheel
   ```

   This will create a `dist` directory containing the built distributions.

3. (Optional) To create a source distribution only:
   ```
   python setup.py sdist
   ```

4. (Optional) To create a wheel distribution only:
   ```
   python setup.py bdist_wheel
   ```

The built packages will be in the `dist` directory and can be installed using pip or distributed as needed.

### Usage

(Add basic commands and examples to get users started)

### Contributing

(Add guidelines for contributing to the project)

## License

This project is licensed under the MIT License.
