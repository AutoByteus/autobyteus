# Autobyteus Lifecycle Event-Sourced Engine Design

**Date:** 2025-12-29
**Status:** Proposal / Design

## 1. Purpose
This document proposes a **fully lifecycle-event-driven, event-sourced** engine model for Autobyteus. In this model:

- **Lifecycle events are the primary extension points.**
- **Handlers are driven exclusively by events.**
- **Status is derived** from the event stream (not manually mutated as the source of truth).
- **Processor pipelines remain** as configurable steps *inside* handlers, not separate lifecycle concepts.

The goal is to make the system simpler to reason about, easier to extend, and easier to debug via event replay.

---

## 2. Core Principles

1. **Events are the source of truth**
   - Every change in behavior or state is caused by an event.
   - The system appends events to a log (in-memory or persisted).

2. **Status is a projection**
   - Agent status is derived by reducing the event stream.
   - Status updates are *not* primary data; they are *computed* from events.

3. **Lifecycle events are the public API**
   - Users inject behavior via lifecycle event processors.
   - Lifecycle events are intentionally coarse-grained and stable.

4. **Processors are internal extension hooks**
   - Processors are invoked by handlers at specific moments.
   - They customize handler behavior but do not replace lifecycle events.

5. **Deterministic handlers**
   - Handlers should be idempotent or safely re-runnable when replaying events.

### 2.1 Control Plane vs. Read Model
In this design we deliberately split responsibilities:

- **Lifecycle events drive the engine** (control plane): they define the runtime flow and handler execution.
- **Status is a derived report** (read model): it summarizes where the agent is for guards, UI, and monitoring.

---

## 3. Event Model

### 3.1 Event Categories

- **Lifecycle Events (user-facing)**
  - Coarse-grained extension points.
  - Current set:
    - `AGENT_READY`
    - `BEFORE_LLM_CALL`
    - `AFTER_LLM_RESPONSE`
    - `BEFORE_TOOL_EXECUTE`
    - `AFTER_TOOL_EXECUTE`
    - `AGENT_SHUTTING_DOWN`

- **Engine Events (internal)**
  - Drive the runtime loop and handlers (user input, tool requests, tool results, errors, etc.).

- **Streaming Events (external)**
  - Observability layer for UI/monitoring (status changes, responses, tool outputs).

### 3.2 Event Envelope (Suggested)
Each event should carry standard metadata:

- `event_id`
- `event_type`
- `timestamp`
- `agent_id`
- `correlation_id`
- `caused_by_event_id`
- `payload`

This enables tracing, replay, and debugging.

### 3.3 Core Lifecycle Event Catalog (Proposed)
This is the **minimal event contract** for a fully lifecycle-event-driven engine.
It is not an exhaustive list of every domain-specific event in the codebase.

| Event | Type | Handler responsibility (summary) | Emits / Next |
|-------|------|----------------------------------|--------------|
| `BOOTSTRAP_STARTED` | internal | Begin bootstrap orchestration **after** minimal runtime init (event loop + input queues) is ready. | `BOOTSTRAP_STEP_REQUESTED` |
| `BOOTSTRAP_STEP_REQUESTED` | internal | Execute one bootstrap step (e.g., workspace, prewarm, system prompt). | `BOOTSTRAP_STEP_COMPLETED` |
| `BOOTSTRAP_STEP_COMPLETED` | internal | Record completion; if steps remain, request next step. | `BOOTSTRAP_STEP_REQUESTED` or `BOOTSTRAP_COMPLETED` |
| `BOOTSTRAP_COMPLETED` | internal | Finalize bootstrap; emit ready signal. | `AGENT_READY` |
| `AGENT_READY` | lifecycle | Notify lifecycle processors and external streams. | `USER_MESSAGE_RECEIVED` (next input) |
| `USER_MESSAGE_RECEIVED` | internal | Run input processors; build prompt context. | `BEFORE_LLM_CALL` |
| `BEFORE_LLM_CALL` | lifecycle | Run lifecycle processors; finalize LLM request. | `LLM_CALL_REQUESTED` |
| `LLM_CALL_REQUESTED` | internal | Send LLM request and await response. | `LLM_RESPONSE_RECEIVED` |
| `LLM_RESPONSE_RECEIVED` | internal | Buffer/assemble response payload. | `AFTER_LLM_RESPONSE` |
| `AFTER_LLM_RESPONSE` | lifecycle | Run lifecycle + LLM response processors; decide next action. | `TOOL_INVOCATION_REQUESTED` or `AGENT_REPLY_READY` |
| `TOOL_INVOCATION_REQUESTED` | internal | Run tool preprocessors; determine approval needs. | `TOOL_APPROVAL_REQUESTED` or `BEFORE_TOOL_EXECUTE` |
| `TOOL_APPROVAL_REQUESTED` | internal | Request external approval. | `TOOL_APPROVED` or `TOOL_DENIED` |
| `TOOL_APPROVED` | internal | Prepare approved invocation. | `BEFORE_TOOL_EXECUTE` |
| `TOOL_DENIED` | internal | Record denial; prepare follow-up response. | `AGENT_REPLY_READY` |
| `BEFORE_TOOL_EXECUTE` | lifecycle | Run lifecycle processors before execution. | `TOOL_EXECUTION_REQUESTED` |
| `TOOL_EXECUTION_REQUESTED` | internal | Execute tool. | `TOOL_EXECUTION_COMPLETED` |
| `TOOL_EXECUTION_COMPLETED` | internal | Capture result payload. | `AFTER_TOOL_EXECUTE` |
| `AFTER_TOOL_EXECUTE` | lifecycle | Run lifecycle + tool result processors; decide next action. | `LLM_CALL_REQUESTED` or `AGENT_REPLY_READY` |
| `AGENT_REPLY_READY` | internal | Enqueue final response for user/system. | `USER_MESSAGE_RECEIVED` (next input) |
| `SHUTDOWN_REQUESTED` | internal | Stop intake, drain queues, start cleanup. | `AGENT_SHUTTING_DOWN` |
| `AGENT_SHUTTING_DOWN` | lifecycle | Run lifecycle processors; release resources. | `SHUTDOWN_COMPLETED` |
| `SHUTDOWN_COMPLETED` | internal | Finalize shutdown; emit terminal stream event. | terminal |
| `ERROR_RAISED` | internal | Record error and short-circuit to shutdown. | `AGENT_SHUTTING_DOWN` |

### 3.4 Lifecycle Event Sequence (Proposed)
The engine runs a **deterministic event sequence**. A typical happy-path flow:

1. `BOOTSTRAP_STARTED`
2. (`BOOTSTRAP_STEP_REQUESTED` → `BOOTSTRAP_STEP_COMPLETED`)* until complete
3. `BOOTSTRAP_COMPLETED` → `AGENT_READY`
4. `USER_MESSAGE_RECEIVED` → `BEFORE_LLM_CALL` → `LLM_CALL_REQUESTED`
5. `LLM_RESPONSE_RECEIVED` → `AFTER_LLM_RESPONSE`
6. `TOOL_INVOCATION_REQUESTED` → `BEFORE_TOOL_EXECUTE` → `TOOL_EXECUTION_REQUESTED` → `TOOL_EXECUTION_COMPLETED` → `AFTER_TOOL_EXECUTE`
7. `AGENT_REPLY_READY`
8. Loop to step 4 or terminate via `SHUTDOWN_REQUESTED`.

Shutdown path:
`SHUTDOWN_REQUESTED` → `AGENT_SHUTTING_DOWN` → `SHUTDOWN_COMPLETED`

---

## 4. Status as a Projection

### 4.1 Status Derivation
Status is computed by reducing the event stream with a pure function:

```
status = reduce(events, initial_status=UNINITIALIZED)
```

### 4.2 Example Mapping (Conceptual)

| Lifecycle Event        | Derived Status Update                       |
|------------------------|--------------------------------------------|
| `AGENT_READY`          | `BOOTSTRAPPING` → `IDLE`                   |
| `BEFORE_LLM_CALL`      | `PROCESSING_USER_INPUT` → `AWAITING_LLM_RESPONSE` |
| `AFTER_LLM_RESPONSE`   | `AWAITING_LLM_RESPONSE` → `ANALYZING_LLM_RESPONSE` |
| `BEFORE_TOOL_EXECUTE`  | `AWAITING_TOOL_APPROVAL` or `PROCESSING_TOOL_RESULT` → `EXECUTING_TOOL` |
| `AFTER_TOOL_EXECUTE`   | `EXECUTING_TOOL` → `PROCESSING_TOOL_RESULT` |
| `AGENT_SHUTTING_DOWN`  | any → `SHUTTING_DOWN`                      |

Status managers become **projection engines** rather than mutation controllers.

### 4.3 Status as a Guard (Derived Read Model)
In a fully event‑sourced engine, status is **optional for correctness** but still **useful as a guard rail**:

- **Behavior gating**: reject or queue input during `BOOTSTRAPPING` / `SHUTTING_DOWN`.
- **Safety checks**: avoid tool execution unless the derived status allows it.
- **Observability**: expose a simple status for UI/monitoring without scanning the full event stream.

Status must remain **derived only** (no direct mutation) to preserve the event‑sourced contract.

---

## 5. Runtime Flow (Event-Sourced)

### 5.0 Runtime Init (Pre-Event, Minimal)
Before any event can be handled, the engine must bring up the **minimal runtime**:

1. Create the worker event loop.
2. Initialize the **input event queues** (the event intake surface).
3. Instantiate the dispatcher/handler registry (if not already constructed).

This phase is intentionally **not event-driven** because it is the prerequisite for
event delivery. It should be as small and deterministic as possible.

**Rule of thumb:** core input queues and the dispatcher belong here; bootstrap steps may
initialize **auxiliary resources** (tool registries, streaming sinks, caches, prewarmers),
but should not be required for basic event routing to function.

### 5.1 Bootstrap
1. **After runtime init**, append `BOOTSTRAP_STARTED` into the internal system queue.
2. A **bootstrap handler** orchestrates steps via `BOOTSTRAP_STEP_REQUESTED` → `BOOTSTRAP_STEP_COMPLETED`.
3. When complete, `BOOTSTRAP_COMPLETED` emits `AGENT_READY`.
4. Status projection resolves to `IDLE`.

During bootstrap, the engine may **gate** or **defer** non‑internal events
until `AGENT_READY` to avoid handling user/tool events before the system is fully prepared.

**Concrete dispatch policy (recommended):**
- While status is `BOOTSTRAPPING`, only the **internal system queue** is serviced.
- Other queues continue to accept events (buffered), but dispatch is deferred.
- Once `AGENT_READY` is emitted, normal queue priority resumes.

### 5.2 User Message Flow
1. `USER_MESSAGE_RECEIVED` event appended.
2. Handler runs input processors.
3. `BEFORE_LLM_CALL` lifecycle event emitted.
4. `LLM_CALL_REQUESTED` handler runs.
5. `LLM_RESPONSE_RECEIVED` event appended.
6. `AFTER_LLM_RESPONSE` lifecycle event emitted.
7. LLM response processors run.

### 5.3 Tool Flow
1. `TOOL_INVOCATION_REQUESTED` event appended.
2. Tool preprocessors run (and approval if required).
3. `BEFORE_TOOL_EXECUTE` lifecycle event emitted.
4. `TOOL_EXECUTION_REQUESTED` handler executes tool.
5. `TOOL_EXECUTION_COMPLETED` event appended.
6. `AFTER_TOOL_EXECUTE` lifecycle event emitted.
7. Tool result processors run.

---

## 6. Processor Pipelines (Inside Handlers)

Processors remain as **internal, ordered pipelines** owned by handlers:

- Input processors
- System prompt processors (bootstrap only)
- LLM response processors
- Tool invocation preprocessors
- Tool execution result processors

**Key rule:** processors do not define lifecycle. They *customize* how handlers respond to events.

---

## 7. Extension Model

### 7.1 User Extensions
Users extend the system by registering **lifecycle event processors**:

- Coarse-grained hooks for stable customization.
- Easy to reason about, low coupling.

### 7.2 Engine Extensions
Framework developers can:

- Add new internal event types.
- Add new handlers and processor pipelines.
- Introduce new lifecycle events (rare, deliberate).

---

## 8. Event Store and Replay (Optional)

Event sourcing enables advanced capabilities:

- **Replay**: Rebuild agent state from the event stream.
- **Time Travel Debugging**: Inspect when/why a handler ran.
- **Audit Trails**: Persist event logs for compliance or analytics.

The initial implementation may use in-memory event logs, with optional persistence later.

---

## 9. Benefits vs. Current Model

**Benefits**
- Clear source of truth (events)
- Simpler mental model for extension
- Status becomes transparent and derived
- Easier debugging and replay

**Tradeoffs**
- Requires consistent event emission
- Handlers must be idempotent or replay-safe
- Larger event volume

---

## 10. Implementation Notes (Phased)

1. **Introduce event envelopes** and a basic event log.
2. **Emit lifecycle events consistently** from handlers.
3. **Refactor status managers into projections.**
4. **Ensure handlers are replay-safe.**

---

## 11. Key Takeaway

A lifecycle event‑sourced design keeps **events as the single source of truth**, treats **status as a derived projection**, and positions **processors as optional customization hooks inside handlers**. This preserves the clarity of the current processor pipeline while making the overall engine simpler, more extensible, and easier to debug.

---

## Appendix A. Current Implementation (Agent Event Flow Map)

This appendix captures the **current agent runtime behavior** in code. It is intentionally concrete and may diverge from the proposal above.

### High-Level Data Flow

1. External inputs (user, inter-agent, approvals) and internal events are enqueued into `AgentInputEventQueueManager`.
2. `AgentWorker` pulls the next event (internal-only while bootstrapping).
3. `WorkerEventDispatcher` appends the event to the event store (if configured), **derives status**, emits lifecycle + external status notifications, then dispatches to a handler.
4. The handler may enqueue additional events, continuing the chain.

### Event Pipeline (Primary)

#### User Input -> LLM -> Response

| Event | Handler | Emits (next events) | Notes |
| --- | --- | --- | --- |
| `UserMessageReceivedEvent` | `UserInputMessageEventHandler` | `LLMUserMessageReadyEvent` | Routes all user/system/tool/inter-agent input through the same input pipeline. |
| `LLMUserMessageReadyEvent` | `LLMUserMessageReadyEventHandler` | `LLMCompleteResponseReceivedEvent` | Streams chunks to notifier, aggregates full response. |
| `LLMCompleteResponseReceivedEvent` | `LLMCompleteResponseReceivedEventHandler` | (Processors may emit `PendingToolInvocationEvent`) | Always notifies a complete response event. |

Additional note: after `LLMCompleteResponseReceivedEvent` is handled, the dispatcher may enqueue `AgentIdleEvent` if there are no pending tool approvals and the tool invocation queue is empty.

#### Tool Invocation and Results

| Event | Handler | Emits (next events) | Notes |
| --- | --- | --- | --- |
| `PendingToolInvocationEvent` | `ToolInvocationRequestEventHandler` | `ToolResultEvent` (auto) or approval notification | If manual approval is needed, it stores pending invocation and emits an approval request (not an event). |
| `ToolExecutionApprovalEvent` | `ToolExecutionApprovalEventHandler` | `ApprovedToolInvocationEvent` (approved) or `LLMUserMessageReadyEvent` (denied) | Denials go back to the LLM. |
| `ApprovedToolInvocationEvent` | `ApprovedToolInvocationEventHandler` | `ToolResultEvent` | Executes tool after approval. |
| `ToolResultEvent` | `ToolResultEventHandler` | `UserMessageReceivedEvent` (aggregated results) | Aggregates multi-tool results into one LLM turn. |

#### Inter-Agent Messages

| Event | Handler | Emits (next events) | Notes |
| --- | --- | --- | --- |
| `InterAgentMessageReceivedEvent` | `InterAgentMessageReceivedEventHandler` | `UserMessageReceivedEvent` | Normalizes inter-agent traffic into the same pipeline. |

### Bootstrapping Flow (Internal)

Runtime init is **not** an event. It happens once in `AgentWorker._runtime_init` to create the event store, status deriver, and input queues.

| Event | Handler | Emits (next events) | Notes |
| --- | --- | --- | --- |
| `BootstrapStartedEvent` | `BootstrapEventHandler` | `BootstrapStepRequestedEvent` or `BootstrapCompletedEvent` | Starts bootstrap orchestration. |
| `BootstrapStepRequestedEvent` | `BootstrapEventHandler` | `BootstrapStepCompletedEvent` | Executes one step. |
| `BootstrapStepCompletedEvent` | `BootstrapEventHandler` | Next `BootstrapStepRequestedEvent` or `BootstrapCompletedEvent` | Advances the sequence. |
| `BootstrapCompletedEvent` | `BootstrapEventHandler` | `AgentReadyEvent` | Only on success. |
| `AgentReadyEvent` | (no explicit handler) | - | Status derivation drives `IDLE`. |

### Shutdown / Error Flow

| Event | Handler | Emits (next events) | Notes |
| --- | --- | --- | --- |
| `ShutdownRequestedEvent` | (no explicit handler) | - | Status derivation drives `SHUTTING_DOWN`. |
| `AgentStoppedEvent` | (no explicit handler) | - | Status derivation drives `SHUTDOWN_COMPLETE`. |
| `AgentErrorEvent` | (no explicit handler) | - | Status derivation drives `ERROR`. |
| `AgentIdleEvent` | (no explicit handler) | - | Status derivation drives `IDLE`. |

### "Where is this handled?" (Separation of Concerns)

- Runtime init + worker loop: `autobyteus/agent/runtime/agent_worker.py`
- Event queues + priority dispatch: `autobyteus/agent/events/agent_input_event_queue_manager.py`
- Event dispatch + status derivation: `autobyteus/agent/events/worker_event_dispatcher.py`
- Event store: `autobyteus/agent/events/event_store.py`
- Status derivation rules: `autobyteus/agent/status/status_deriver.py`
- Lifecycle + notifier emission: `autobyteus/agent/status/manager.py`
- Event handlers: `autobyteus/agent/handlers/*.py`
- LLM response processors (emit tool events): `autobyteus/agent/llm_response_processor/*.py`
- Tool result processors: `autobyteus/agent/tool_execution_result_processor/*.py`
- Input processors: `autobyteus/agent/input_processor/*.py`

### Status Update Event Contract (External)

Clients receive status changes through a single external event:

- **EventType**: `AGENT_STATUS_UPDATED`
- **StreamEventType**: `AGENT_STATUS_UPDATED`
- **Payload**: `AgentStatusUpdateData`
  - `new_status` (required)
  - `old_status` (optional)
  - `trigger` (optional, schema field)
  - `tool_name` (optional, when tool-related)
  - `error_message` / `error_details` (optional, on error)

**Current emitter note:** the status update builder uses `trigger` in the payload for `PROCESSING_USER_INPUT` events, matching the stream payload schema.
