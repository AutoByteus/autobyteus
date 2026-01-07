# Autobyteus System Architecture & Documentation Catalog

**Status:** Auto-generated from `docs/` analysis.
**Date:** 2026-01-05

## 1. System Overview

Autobyteus is a highly modular, **event-driven** multi-agent framework. It distinguishes itself by using a strictly asynchronous, message-based architecture where every agent, team, and workflow runs in its own thread with a private event loop.

The system is designed around **Concerns** that interact through well-defined **Edges** (Events, Interfaces, and Tool Calls).

### High-Level Mental Model

```mermaid
graph TD
    User((User)) -->|Input| Runtime[Agent/Team Runtime]
    Runtime -->|Dispatch| EventBus[Event Bus & Queues]
    EventBus -->|Event| Handlers[Event Handlers]
    
    subgraph "Core Processing"
        Handlers -->|Invoke| Processors[Processors (Input/Result)]
        Handlers -->|Call| LLM[LLM Module]
        LLM -->|Stream| Parser[Streaming Parser]
        Parser -->|Tool Call| ToolExec[Tool Execution]
    end
    
    subgraph "Knowledge & Capability"
        ToolExec -->|Use| Skills[Skills (Directory-based)]
        ToolExec -->|Run| Terminal[Terminal Tools (PTY)]
    end
    
    ToolExec -->|Result Event| EventBus
    LLM -->|Response Event| EventBus
```

---

## 2. Module Catalog

This catalog maps the system's capabilities to their defining design documents.

### 2.1 Core Runtime & Engine
The heart of the system. It manages the lifecycle, concurrency, and event dispatching.

*   **Event-Driven Core**: How the system uses per-entity event loops and input queues.
    *   *Read:* [`docs/event_driven_core_design.md`](docs/event_driven_core_design.md)
*   **Lifecycle Engine**: The "Event-Sourced" approach where status (`IDLE`, `PROCESSING`) is a projection of the event stream.
    *   *Read:* [`docs/lifecycle_event_sourced_engine_design.md`](docs/lifecycle_event_sourced_engine_design.md)
*   **Agent Processor Design**: The pipeline of processors (Input -> System Prompt -> LLM -> Response -> Tool) that customize handler behavior.
    *   *Read:* [`docs/agent_processor_and_engine_design.md`](docs/agent_processor_and_engine_design.md)
*   **Context Compaction**: Automated summarization to manage context window limits.
    *   *Read:* [`docs/context_compaction.md`](docs/context_compaction.md)

### 2.2 Multi-Agent Coordination (Teams)
How individual agents are composed into collaborative groups.

*   **Team Design**: The graph-based structure of teams and sub-teams, and the `TeamManager` facade.
    *   *Read:* [`docs/agent_team_design.md`](docs/agent_team_design.md)
*   **Runtime & Coordination**: How teams use input queues and the `TaskPlan` to coordinate work (Manual vs. System-Driven modes).
    *   *Read:* [`docs/agent_team_runtime_and_task_coordination.md`](docs/agent_team_runtime_and_task_coordination.md)

### 2.3 Intelligence (LLM)
The module responsible for communicating with AI models.

*   **LLM Module**: The unified interface (`BaseLLM`) and factory for interacting with providers (OpenAI, Anthropic) and runtimes (API, Ollama, MLX).
    *   *Read:* [`docs/llm_module_design.md`](docs/llm_module_design.md)

### 2.4 Capabilities (Tools & Skills)
How the agent interacts with the world.

*   **Tool Configuration**: How tools accept instantiation-time config vs. runtime arguments.
    *   *Read:* [`docs/tool_configuration_design.md`](docs/tool_configuration_design.md)
*   **Streaming Parser**: The state-machine that parses tool calls (`<write_file>`, JSON) from the LLM stream in real-time.
    *   *Read:* [`docs/streaming_parser_design.md`](docs/streaming_parser_design.md)
*   **Tool Call Formatting**: The contract between tool definitions, manifests, and the parser.
    *   *Read:* [`docs/tool_call_formatting_and_parsing.md`](docs/tool_call_formatting_and_parsing.md)
*   **Skills**: The hierarchical, directory-based knowledge system (`SKILL.md`).
    *   *Read:* [`docs/skills_design.md`](docs/skills_design.md)
*   **Terminal Tools**: PTY-based stateful terminal execution.
    *   *Read:* [`docs/terminal_tools.md`](docs/terminal_tools.md)

---

## 3. Reference Graph (Concerns & Interactions)

Understanding the "Edges" between modules.

### The "Execution" Edge (LLM -> Tools)
*   **Interaction**: The LLM generates text -> `StreamingParser` detects intent -> `ToolInvocationAdapter` creates a `ToolInvocation` object -> `ToolExecutionEventHandler` runs the tool.
*   **Key Design**: The *Streaming Parser* [`docs/streaming_parser_design.md`] is the critical bridge here, ensuring safe, partial rendering while accumulating the structured command.

### The "Coordination" Edge (Agent -> Team)
*   **Interaction**: An Agent needs to talk to another -> It uses the `send_message_to` tool -> `TeamManager` routes the `InterAgentMessageRequestEvent` to the recipient's input queue.
*   **Key Design**: Agents never call each other directly; they dispatch events through the *Team Runtime* [`docs/agent_team_runtime_and_task_coordination.md`].

### The "Knowledge" Edge (Agent -> Skills)
*   **Interaction**: Agent loads a skill -> Receives `SKILL.md` (the map) -> Decides to read a specific file -> Uses `read_file` with an absolute path constructed from the skill's root.
*   **Key Design**: "Just-In-Time" loading to save context window [`docs/skills_design.md`].

### The "Observation" Edge (Internal -> External)
*   **Interaction**: Events occur internally -> `AgentEventMultiplexer` bridges them to an `AgentEventStream` -> UI/CLI consumes the stream.
*   **Key Design**: Separation of the internal control loop (Events) from external observability (Streams) [`docs/event_driven_core_design.md`].
