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

Lifecycle Events represent **actionable moments** that occur during status transitions. Developers can register **Lifecycle Processors** to run custom logic when these events fire. This replaces the legacy "Phase Hooks" system.

**Key Lifecycle Events:**

- `AGENT_READY`: Fires when bootstrapping finishes and the agent becomes `IDLE`. Good for one-time initialization.
- `BEFORE_LLM_CALL`: Fires right before sending a request to the LLM. useful for modifying prompt context.
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

1.  **Trigger**: The `AgentRuntime` determines it needs to change state (e.g., "Tool finished running").
2.  **Request**: It calls `AgentStatusManager._transition_status(new_status=...)`.
3.  **Lifecycle Hooks**: The Manager calculates the equivalent `LifecycleEvent` (if any) and executes all registered `LifecycleProcessors`.
    - _Example_: Transitioning `EXECUTING_TOOL` -> `PROCESSING_TOOL_RESULT` triggers `AFTER_TOOL_EXECUTE`.
4.  **State Change**: The `AgentContext.current_status` is updated.
5.  **External Notification**: The Manager calls `AgentExternalEventNotifier.notify_status_*()`, which emits the persistent `EventType` to the Event Bus.

## Extending the Agent

### Adding Custom Logic (Internal)

To inject custom code into the agent loop, implement a `BaseLifecycleProcessor`:

```python
from autobyteus.agent.lifecycle import BaseLifecycleProcessor, LifecycleEvent

class MyCustomLogger(BaseLifecycleProcessor):
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

## Reference Map

| Old Term ("Phase")      | New Term ("Status")  | Purpose                    |
| :---------------------- | :------------------- | :------------------------- |
| `AgentOperationalPhase` | `AgentStatus`        | State Machine Enum         |
| `AgentPhaseManager`     | `AgentStatusManager` | State Controller           |
| `Phase Hook`            | `LifecycleProcessor` | Custom Logic Plugin        |
| `notify_phase_*`        | `notify_status_*`    | Status Change Notification |
