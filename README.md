# Autobyteus

Autobyteus is an open-source coding assistance tool designed to enhance the software development workflow by making it context-aware. Each step in the workflow is interactive through a user-friendly interface, incorporating the entire software development lifecycle into each stage.

## Architecture

Autobyteus is built with a modular, event-driven architecture designed for extensibility and clear separation of concerns. The key components are:

-   **Agent Core**: The heart of the system, comprising an `Agent` facade that provides the primary user-facing API. This facade communicates with an `AgentRuntime`, which manages an `AgentWorker` running in a dedicated thread. This design ensures non-blocking agent operations.
-   **Context & Configuration**: Agent behavior is defined through a clear configuration (`AgentConfig`) and its dynamic state is managed in `AgentRuntimeState`. These are bundled into a comprehensive `AgentContext` that is available to all components during runtime, providing a single source of truth for an agent's status and capabilities.
-   **Event-Driven System**: Agents operate on an internal event loop. Actions (like receiving user messages or tool results) are translated into events and placed on internal queues. `EventHandlers` process these events, containing the core logic for how an agent thinks and acts. This decouples logic and makes the system easy to extend.
-   **Pluggable Processors**: The framework uses a pipeline of processors to modify data at key stages. `SystemPromptProcessors` dynamically build the final system prompt (e.g., by injecting tool definitions), `InputProcessors` preprocess user messages, and `LLMResponseProcessors` parse outputs from the language model (e.g., to detect tool usage).
-   **Tooling**: Agents can be extended with `Tools`, which are self-contained capabilities that can be called by the LLM. The system includes built-in tools (like `SendMessageTo` for inter-agent communication) and supports custom tools.
-   **Multi-Agent Systems**: The `AgentGroup` and `AgenticWorkflow` abstractions provide powerful, high-level APIs for orchestrating multiple agents to collaborate on complex tasks.
-   **Remote Agents**: Built-in RPC capabilities allow for communication with agents running in separate processes or on different machines, enabling distributed agent systems.

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
