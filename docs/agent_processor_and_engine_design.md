# Autobyteus Agent Framework: Engine, Tools, and Processor Design

**Date:** 2025-12-29
**Status:** Living Document

## 1. Introduction

The **Autobyteus Agent Framework** is built on a highly modular, event-driven architecture designed to support complex, stateful agents. At its core, the framework separates the **Engine** (execution runtime) from the **Processors** (logic units) and **Tools** (capabilities). This separation allows for granular control over the agent's lifecycle, from input processing to tool execution and response generation.

This document details the design and implementation of these three pillars.

---

## 2. Core Engine Architecture

The engine provides the runtime environment for agents. It is strictly **event-driven**, ensuring that all actions—whether internal state changes or external side effects—are the result of discrete events processing.

### 2.1. Event-Driven Runtime

Each agent runs within its own isolated environment, characterized by:

- **Dedicated Worker Thread**: Each agent (and AgentTeam/Workflow) operates on its own worker thread, created by a shared `AgentThreadPoolManager`.
- **Private Event Loop**: Inside the worker thread, a private `asyncio` event loop manages concurrent tasks. This ensures isolation and prevents blocking operations in one agent from affecting others.
- **Status Management**: The engine maintains a state machine (e.g., `IDLE`, `PROCESSING`, `AWAITING_INPUT`). Status updates are derived from events and emitted by the `StatusManager`.

### 2.2. Event Processing Pipeline

The flow of execution follows a standard pipeline:

1.  **Submission**: Events (e.g., `UserMessageReceivedEvent`) are submitted to the runtime safely from any thread.
2.  **Queueing**: Events are routed to specific input queues based on their type (e.g., user messages, tool results, internal signals). This allows for priority handling (e.g., system signals > user input).
3.  **Dispatching**: The `WorkerEventDispatcher` picks the next event and routes it to the appropriate **Handler**.
4.  **Handling**: Handlers execute business logic. Crucially, **Processors** are often invoked within these handlers to perform specific transformations or logic.

---

## 3. Processor Architecture

Processors are the "functional units" of the agent. They intercept data at specific points in the lifecycle to modify state, transform content, or trigger side effects.

### 3.1. The Processor Pattern

All processors share a common architectural pattern:

- **Base Classes**: Each type has an abstract base class (e.g., `BaseLLMResponseProcessor`) defining its contract.
- **Metaclass Registration**: Processors are automatically registered via metaclasses (e.g., `LLMResponseProcessorMeta`), allowing for easy discovery.
- **Configuration (`ProcessorOption`)**: Processors are enabled/disabled via `ProcessorOption` objects, which define their name and whether they are `mandatory`.
- **Ordering**: Processors of the same type run in a specific sequence defined by their `get_order()` method.

### 3.2. Types of Processors

#### A. Input Processors (`agent/input_processor`)

- **Role**: Intercept and modify the `AgentInputUserMessage` before it is converted into a prompt for the LLM.
- **Use Cases**:
  - Content sanitization or PII redaction.
  - Appending context or instructions dynamically.
  - Expanding macros or shortcuts in user input.

#### B. System Prompt Processors (`agent/system_prompt_processor`)

- **Role**: Dynamically construct or modify the system prompt sent to the LLM.
- **Key Implementation**: `ToolManifestInjectorProcessor`.
  - This processor is responsible for injecting the descriptions of available tools (the "Manifest") into the system prompt, ensuring the LLM knows what actions it can take.
  - It typically replaces a placeholder like `{{tools}}` with the formatted tool definitions.
- **Execution Timing (Important)**: System prompt processors run **once during bootstrapping** in `SystemPromptProcessingStep`. They are **not** invoked before every LLM call.

#### C. LLM Response Processors (`agent/llm_response_processor`)

- **Role**: Optional post-processing of the `CompleteResponse` received from the LLM.
- **Tool Parsing Note**: Tool invocation parsing is handled during streaming by
  `LLMUserMessageReadyEventHandler` using `StreamingResponseHandler` and the
  `ToolInvocationAdapter`. LLM response processors are no longer required by default.

#### D. Tool Invocation Preprocessors (`agent/tool_invocation_preprocessor`)

- **Role**: Intercept a `ToolInvocation` _after_ the LLM has requested it but _before_ it is executed.
- **Use Cases**:
  - **Validation**: Checking if arguments match the schema or constraints.
  - **Approval**: Pausing execution to ask for human confirmation (Human-in-the-loop).
  - **Rewriting**: modifying arguments on the fly (e.g., resolving relative paths).

#### E. Tool Execution Result Processors (`agent/tool_execution_result_processor`)

- **Role**: Process the output returned by a tool.
- **Use Cases**:
  - **Formatting**: converting raw JSON or large text into a summary for the LLM.
  - **Artifact Extraction**: Saving images or files generated by the tool to a separate storage and replacing them with a link in the conversation history.

---

## 4. Tooling Subsystem

The tooling subsystem bridges the gap between the LLM's text output and actual code execution.

### 4.1. Definition and Registry

- **`ToolDefinition`**: The canonical source of truth for a tool, containing its name, description, and schema (arguments structure).
- **`ToolRegistry`**: Stores all available definitions.

### 4.2. Formatting (Manifest)

The system must tell the LLM how to call tools. This is handled by **Formatters**:

- **Provider-Aware**: Different LLMs (OpenAI vs. Anthropic) require different schema formats (JSON Schema vs. XML).
- **Manifest Generation**: The `ToolManifestProvider` builds the schema and usage examples, which the `ToolManifestInjectorProcessor` (see above) inserts into the prompt.

### 4.3. Parsing (Execution)

When the LLM responds, the system interprets intent during streaming:

- **`StreamingParser`**: FSM-based streaming parser that detects XML/JSON/sentinel tool blocks.
- **`ToolInvocationAdapter`**: Converts completed tool segments into `ToolInvocation` objects.

---

## 5. Integration Flow: A Life of a Request

1.  **User Input**: User sends "List files in src".
2.  **Engine**: Enqueues `UserMessageReceivedEvent`.
3.  **Input Processor**: Runs (no changes).
4.  **System Prompt Processor (Bootstrap)**: `ToolManifestInjectorProcessor` has already inserted the schema for `list_directory` into the system prompt during bootstrapping.
5.  **LLM Call**: Agent sends prompt to LLM.
6.  **LLM Response**: LLM returns text/JSON requesting `list_directory(path="src")`.
7.  **Streaming Parser**: `LLMUserMessageReadyEventHandler` parses the stream, identifies tool calls, and enqueues `PendingToolInvocationEvent`.
8.  **Preprocessor**: Checks if `list_directory` is allowed (e.g., within sandbox).
9.  **Execution**: Tool runs, returns list of files.
10. **Result Processor**: Formats the file list.
11. **Context Update**: Result is added to chat history.
12. **Loop**: Agent waits for next event or generates a final answer.

---

## 6. Lifecycle Events vs. Pipeline Processors (Clarifying the Boundaries)

Autobyteus exposes **two** extensibility mechanisms that often occur near the same moments:

- **Pipeline processors** (Input, System Prompt, LLM Response, Tool Pre/Post, Tool Result) are invoked by **event handlers**.
- **Lifecycle processors** (`agent/lifecycle/`) are invoked by **status transitions** inside `AgentStatusManager`.

### Lifecycle Event Enum (`agent/lifecycle/events.py`)

The `LifecycleEvent` enum defines user-facing hook points:

| Lifecycle Event       | Triggered When                                                              |
| --------------------- | --------------------------------------------------------------------------- |
| `AGENT_READY`         | After bootstrap completes, agent enters `IDLE`                              |
| `BEFORE_LLM_CALL`     | Status transitions to `AWAITING_LLM_RESPONSE`                               |
| `AFTER_LLM_RESPONSE`  | Status transitions from `AWAITING_LLM_RESPONSE` to `ANALYZING_LLM_RESPONSE` |
| `BEFORE_TOOL_EXECUTE` | Status transitions to `EXECUTING_TOOL`                                      |
| `AFTER_TOOL_EXECUTE`  | Status transitions from `EXECUTING_TOOL`                                    |
| `AGENT_SHUTTING_DOWN` | Status transitions to `SHUTTING_DOWN`                                       |

### Ordering Summary (Implemented Behavior)

1. System prompt processors run **once at bootstrap** (not before each LLM call).
2. `BEFORE_LLM_CALL` lifecycle processors run when entering `AWAITING_LLM_RESPONSE`, before the LLM request is sent.
3. `AFTER_LLM_RESPONSE` lifecycle processors run when entering `ANALYZING_LLM_RESPONSE`, before LLM response processors run.
4. `BEFORE_TOOL_EXECUTE` lifecycle processors run before tool handlers execute.
5. `AFTER_TOOL_EXECUTE` lifecycle processors run before tool result processors run.

### Key Module Locations

- **Lifecycle processors**: `autobyteus/agent/lifecycle/`
- **Status derivation**: `autobyteus/agent/status/status_deriver.py`
- **Lifecycle execution**: `autobyteus/agent/status/manager.py`
