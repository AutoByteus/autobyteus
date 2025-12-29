# Autobyteus Event-Driven Core Design

## 1. Scope and Goals
This document describes the **event-driven core** that powers Autobyteus agents, agent teams, and workflows. It focuses on how the system:

- creates per-entity event loops,
- routes events through input queues,
- dispatches events to handlers with status management,
- streams events outward for UI/monitoring,
- and shuts down cleanly.

The intent is to provide a clear mental model for extending or debugging the runtime.

---

## 2. Core Runtime Layers (Agent, Team, Workflow)
Autobyteus uses a consistent pattern across Agent, AgentTeam, and Workflow runtimes.

### 2.1 Runtime Wrapper
Each runtime (`AgentRuntime`, `AgentTeamRuntime`, `WorkflowRuntime`) owns:

- the **context** (config + state),
- a **status manager**,
- an **external event notifier** (for streaming + UI),
- and a **worker** that runs the event loop.

The runtime provides the public API:
- `start()` to spin up the worker thread,
- `submit_event()` to enqueue input events,
- `stop()` to shut down cleanly.

### 2.2 Worker Thread + Event Loop
Each worker (`AgentWorker`, `AgentTeamWorker`, `WorkflowWorker`) creates its own thread and **private asyncio event loop**.

- The worker thread is created by a shared `AgentThreadPoolManager` (singleton thread pool).
- Inside the thread, the worker creates and owns an asyncio loop.
- The worker runs `async_run()` for the lifecycle (bootstrap → event loop → shutdown).

### 2.3 Bootstrap and Shutdown
Bootstrap steps run **inside the worker loop** so that queues and async components are bound to the correct loop.

Agent bootstrap steps include (default order):
1. `AgentRuntimeQueueInitializationStep` (creates input queues)
2. `WorkspaceContextInitializationStep`
3. `McpServerPrewarmingStep`
4. `SystemPromptProcessingStep`

A successful bootstrap enqueues `AgentReadyEvent` (or `WorkflowReadyEvent` / `AgentTeamReadyEvent`).

Shutdown is orchestrated inside the worker loop (e.g., `AgentShutdownOrchestrator`) after the main loop exits.

---

## 3. Input Event Queues
### 3.1 AgentInputEventQueueManager
The agent runtime has **multiple input queues**, each dedicated to a class of events:

- user messages
- inter-agent messages
- tool invocation requests
- tool results
- tool approval
- internal system events

This separation allows the runtime to coordinate priorities and preserve order **per queue**.

### 3.2 Deterministic Queue Selection
`get_next_input_event()` in `AgentInputEventQueueManager` uses a **two-phase strategy** to prevent reordering:

1. **Serve buffered items first** (FIFO per queue).
2. If none buffered, wait on all queues with `asyncio.wait(..., FIRST_COMPLETED)`.
   - Completed items are **buffered**, not requeued.
   - Pending tasks are cancelled.
3. Return the highest-priority buffered event.

Priority order is deterministic (user → inter-agent → tool invocation → tool result → tool approval → internal system). This avoids the previous bug where ready events were reinserted at the tail and changed order.

### 3.3 Team/Workflow Queue Managers
AgentTeam and Workflow runtimes use simpler queue managers with two queues:

- user message queue
- internal system event queue

Their workers wait on both queues with `asyncio.wait(FIRST_COMPLETED)`.

---

## 4. Event Processing Pipeline
### 4.1 Submitting Events (Cross-Thread)
External callers submit events via the runtime (`submit_event`). The runtime:

1. retrieves the worker event loop,
2. schedules a coroutine with `asyncio.run_coroutine_threadsafe`,
3. enqueues the event into the correct queue.

This makes the queueing thread-safe and ensures all queue ops happen inside the worker loop.

### 4.2 Worker Main Loop (Agent)
The agent worker loop looks like:

1. await `get_next_input_event()` (with timeout so stop signals can be honored)
2. dispatch the event through `WorkerEventDispatcher`
3. yield to loop (`await asyncio.sleep(0)`) so other tasks can run

### 4.3 Dispatch + Status Management
`WorkerEventDispatcher` does two jobs:

- **Status transitions** (e.g., IDLE → PROCESSING_USER_INPUT → AWAITING_LLM_RESPONSE → ANALYZING → IDLE)
- **Handler invocation** using the `EventHandlerRegistry`

If a handler throws, the dispatcher emits `AgentErrorEvent` and notifies the status manager to enter ERROR.

### 4.4 Handlers
Handlers are registered by event type and encapsulate business logic (LLM calls, tool execution, messaging). They can enqueue follow-up events to continue the flow.

---

## 5. Event Streaming and Multiplexing
The event-driven core also emits **external, streamable events** for UIs and monitoring:

- `AgentExternalEventNotifier` emits status changes and output data events.
- `AgentEventStream` subscribes to the notifier and converts events to stream records.
- `AgentEventBridge` forwards an agent’s stream into a workflow notifier.
- `AgentEventMultiplexer` manages multiple bridges so a workflow can aggregate events from its agents and sub-workflows.

This decouples internal control flow (queues) from external observability (streams).

---

## 6. Lifecycle Sequences (Agent)
### 6.1 Startup
1. `AgentRuntime.start()` → worker thread created.
2. Worker creates event loop → runs bootstrap.
3. `AgentRuntimeQueueInitializationStep` creates input queues.
4. Bootstrap finishes → `AgentReadyEvent` enqueued.
5. Dispatcher handles `AgentReadyEvent` → status transitions to IDLE.

### 6.2 Event Handling (Typical)
1. External `UserMessageReceivedEvent` is submitted.
2. Event hits `user_message_input_queue`.
3. Dispatcher routes to handler.
4. Handler enqueues `LLMUserMessageReadyEvent` → LLM call.
5. Tool events may enqueue `PendingToolInvocationEvent` → approval or auto-execution.
6. `ToolResultEvent` and `LLMCompleteResponseReceivedEvent` drive the agent back to IDLE.

### 6.3 Shutdown
1. `AgentRuntime.stop()` triggers status transition to SHUTTING_DOWN.
2. Worker stop signal set; `AgentStoppedEvent` enqueued.
3. Worker exits loop and runs shutdown orchestrator.
4. Runtime completes final status transition.

---

## 7. Concurrency and Safety Guarantees
- **Isolation:** Each agent/team/workflow runs in its own thread + event loop.
- **Thread-safe submission:** All input queue ops happen via run_coroutine_threadsafe on the worker loop.
- **Ordering:** Each queue preserves FIFO; inter-queue ordering is deterministic via priority.
- **Backpressure:** `asyncio.Queue(maxsize=queue_size)` can be configured for bounded queues.
- **Error containment:** Dispatcher errors are caught, reported, and translated into error events/status transitions.

---

## 8. Extension Points
- **Add new events:** Define a dataclass event and register a handler in `EventHandlerRegistry`.
- **Adjust queue priorities:** Update `_queue_priority` in `AgentInputEventQueueManager`.
- **Add new bootstrap steps:** Extend `AgentBootstrapper` or pass custom steps.
- **Stream new outputs:** Add notifier events and map them in `AgentEventStream`.

---

## 9. Key Files (Reference)
- Agent runtime loop: `autobyteus/agent/runtime/agent_worker.py`
- Agent queue manager: `autobyteus/agent/events/agent_input_event_queue_manager.py`
- Agent dispatcher: `autobyteus/agent/events/worker_event_dispatcher.py`
- Agent runtime wrapper: `autobyteus/agent/runtime/agent_runtime.py`
- Workflow/team workers: `autobyteus/workflow/runtime/workflow_worker.py`, `autobyteus/agent_team/runtime/agent_team_worker.py`
- Stream multiplexing: `autobyteus/workflow/streaming/agent_event_multiplexer.py`
