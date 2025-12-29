# Agent Status and Lifecycle System

## Overview

The Autobyteus Agent framework uses a **Status** and **Lifecycle** system to manage state, execute hooks, and notify external systems. This architecture separates _where the agent is_ (Status) from _what just happened_ (Lifecycle Events), providing a predictable and extensible foundation.

## Core Concepts

### 1. Agent Status (`AgentStatus`)

The `AgentStatus` enum represents the **current operational state** of the agent. It describes "where" the agent is in its execution loop. The agent can only be in one status at a time.

**Key Statuses:**

- `UNINITIALIZED`: Agent created but not started.
- `BOOTSTRAPPING`: Loading tools, prompts, and memory.
- `IDLE`: Waiting for a new task or message.
- `PROCESSING_USER_INPUT`: Evaluating a new user request.
- `AWAITING_LLM_RESPONSE`: Network request sent to LLM, waiting for tokens.
- `EXECUTING_TOOL`: Running a specific tool (e.g., `bash`, `read_file`).
- `ERROR`: Unrecoverable error state.
- `SHUTDOWN_COMPLETE`: Clean exit.

**Transition Logic:**
Transitions are managed by the `AgentStatusManager`. For example, when the LLM returns a response, the manager transitions the agent from `AWAITING_LLM_RESPONSE` -> `ANALYZING_LLM_RESPONSE`.

### 2. Lifecycle Events (`LifecycleEvent`)

Lifecycle Events represent **actionable moments** that occur during status transitions. Developers can register **Lifecycle Processors** to run custom logic when these events fire.

**Key Lifecycle Events:**

- `AGENT_READY`: Fires when bootstrapping finishes and the agent becomes `IDLE`. Good for one-time initialization.
- `BEFORE_LLM_CALL`: Fires right before sending a request to the LLM. Useful for modifying prompt context.
- `AFTER_LLM_RESPONSE`: Fires when the LLM response is received but before it is processed.
- `BEFORE_TOOL_EXECUTE`: Fires before a tool runs.
- `AFTER_TOOL_EXECUTE`: Fires after a tool completes.

### 3. Comparison: Lifecycle vs. External Events

| Feature       | Lifecycle Events (Hooks)                                   | External Events (Notifiers)                                     |
| :------------ | :--------------------------------------------------------- | :-------------------------------------------------------------- |
| **Purpose**   | **Control & Mutation**. Change how the agent behaves.      | **Observation**. Display or track what the agent is doing.      |
| **Execution** | **Synchronous / Blocking**. The agent waits for your code. | **Fire-and-Forget**. The agent continues working immediately.   |
| **Power**     | **High**. Can modify `AgentContext`, memory, or prompt.    | **Read-Only**. Typically just receives a status update payload. |
| **Analogy**   | The **Editor** of a movie (changes the scenes).            | The **Audience** (watches the movie).                           |

### 4. External Events (`EventType`)

While _Status_ and _Lifecycle_ are internal, **Events** are broadly emitted to the outside world via `AgentExternalEventNotifier`.

> **Note**: Notifiers typically receive the `old_status` as an argument. This provides context (e.g., "We entered IDLE from ERROR") which is critical for debugging and UI updates.

**Naming Convention:**
Legacy "Phase" event names have been deprecated. The new standard is `AGENT_STATUS_*`.

- `AGENT_STATUS_BOOTSTRAPPING_STARTED`
- `AGENT_STATUS_IDLE_ENTERED`
- `AGENT_STATUS_EXECUTING_TOOL_STARTED`

## Architecture: How It Works

1.  **Trigger**: The event dispatcher receives an event (e.g., `LLMUserMessageReadyEvent`).
2.  **Status Request**: The dispatcher asks `AgentStatusManager` to transition status.
3.  **Lifecycle Processors**: The manager maps the status transition to a `LifecycleEvent` and runs matching processors.
    - _Example_: Transitioning to `AWAITING_LLM_RESPONSE` triggers `BEFORE_LLM_CALL`.
4.  **State Change**: The `AgentContext.current_status` is updated.
5.  **External Notification**: The manager calls `AgentExternalEventNotifier.notify_status_*()`, which emits `EventType` for external observers.

## Processor vs. Lifecycle Processor (Ordering Contract)

There are two extensibility mechanisms, and they run at different times:

- **Pipeline processors** (input, system prompt, LLM response, tool pre/post, tool result) are invoked by event handlers.
- **Lifecycle processors** run on status transitions inside the `AgentStatusManager`.

**Current ordering (important for clarity):**

1. **Bootstrapping**: `SystemPromptProcessingStep` runs once during bootstrapping to build the system prompt and configure the LLM. It does **not** run before each LLM call.
2. **Before LLM call**: `BEFORE_LLM_CALL` lifecycle processors run when the agent transitions to `AWAITING_LLM_RESPONSE`, **before** the handler makes the LLM request.
3. **After LLM response**: `AFTER_LLM_RESPONSE` lifecycle processors run when transitioning to `ANALYZING_LLM_RESPONSE`, **before** LLM response processors are applied.
4. **Before tool execution**: `BEFORE_TOOL_EXECUTE` lifecycle processors run when transitioning to `EXECUTING_TOOL`, **before** the tool handler executes the tool.
5. **After tool execution**: `AFTER_TOOL_EXECUTE` lifecycle processors run when transitioning out of `EXECUTING_TOOL`, **before** tool result processors run.

## Extending the Agent

### Adding Custom Logic (Internal)

To inject custom code into the agent loop, implement a `BaseLifecycleEventProcessor`:

```python
from autobyteus.agent.lifecycle import BaseLifecycleEventProcessor, LifecycleEvent

class MyCustomLogger(BaseLifecycleEventProcessor):
    @property
    def event(self) -> LifecycleEvent:
        return LifecycleEvent.BEFORE_LLM_CALL

    async def process(self, context: 'AgentContext', event_data: dict) -> None:
        print(f"About to call LLM with context: {context}")
```

### Listening to Updates (External)

To update a UI or database based on agent progress, subscribe to the Event Bus:

```python
event_emitter.on(EventType.AGENT_STATUS_EXECUTING_TOOL_STARTED, my_handler)
```
