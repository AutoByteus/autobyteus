# Autobyteus Agent Team Design

## 1. Purpose and Scope
Agent Teams provide the **multi-agent orchestration layer** in Autobyteus. A team is a managed graph of agents and sub-teams that:

- routes messages to the correct node,
- lazily starts agents/sub-teams on demand,
- coordinates task plans and optional system-driven notifications,
- aggregates events into a single team stream,
- and manages clean shutdown across all nodes.

This document focuses on the **agent_team** package and how it integrates with the runtime and event-driven core.

---

## 2. Core Concepts
### 2.1 Team Graph (Nodes + Dependencies)
Teams are defined as graphs of **TeamNodeConfig** objects. Each node is either:

- a single **AgentConfig** (agent node), or
- a full **AgentTeamConfig** (sub-team node).

Dependencies are explicit per-node, allowing teams to model execution ordering and coordination. Each node has a unique name enforced by the builder.

### 2.2 Team Facade vs Runtime
- **AgentTeam**: thin, user-facing API (`post_message`, `post_tool_execution_approval`, `start`, `stop`).
- **AgentTeamRuntime**: owns the team’s worker thread, event loop, phase manager, and multiplexer.

The facade forwards all calls to the runtime, ensuring concurrency and event-driven processing.

---

## 3. Team Construction Pipeline
### 3.1 Builder
`AgentTeamBuilder` is the fluent API for constructing a team:

- enforces unique node names,
- captures dependencies,
- sets the coordinator,
- configures `TaskNotificationMode`,
- optionally enforces XML tool format at the team level.

The builder compiles everything into a single immutable **AgentTeamConfig**.

### 3.2 Factory
`AgentTeamFactory` assembles runtime components:

1. `AgentTeamRuntimeState`
2. `AgentTeamContext`
3. Default event handler registry
4. `AgentTeamRuntime`
5. `TeamManager`

The resulting `AgentTeam` facade is returned and cached by the factory.

---

## 4. Runtime Model
### 4.1 Worker Thread + Event Loop
Each team has a dedicated worker thread (via the shared `AgentThreadPoolManager`). Inside it:

- a private asyncio loop is created,
- bootstrap steps run,
- the event loop dispatches team events,
- shutdown steps run after stop.

### 4.2 Input Queues
`AgentTeamInputEventQueueManager` provides two queues:

- `user_message_queue`
- `internal_system_event_queue`

The worker waits on both using `asyncio.wait(FIRST_COMPLETED)`.

### 4.3 Event Dispatcher
`AgentTeamEventDispatcher` routes events to handlers and triggers phase changes:

- `AgentTeamReadyEvent` -> `IDLE`
- Errors -> `ERROR`

---

## 5. TeamManager (Node Lifecycle + Routing)
`TeamManager` is the **central orchestration layer** for nodes.

### 5.1 Lazy Creation
When a message targets a node, `ensure_node_is_ready()`:

- resolves the node by name (or agent_id),
- lazily instantiates the agent/sub-team if missing,
- starts the node if not running,
- waits until it is IDLE (agent or sub-team),
- registers event bridges via the multiplexer.

### 5.2 Routing
`TeamManager` is used by event handlers and tools to route messages:

- `ProcessUserMessageEvent` → to agent or sub-team
- `InterAgentMessageRequestEvent` → via send_message_to tool
- `ToolApprovalTeamEvent` → forwarded to target agent

This guarantees a consistent path for all intra-team communication.

---

## 6. Bootstrap Process (Team Lifecycle)
Team initialization runs inside the worker loop via `AgentTeamBootstrapper`:

1. **Queue initialization** (`AgentTeamRuntimeQueueInitializationStep`)
2. **TaskPlan setup + event bridging** (`TeamContextInitializationStep`)
3. **Optional notifier** (SYSTEM_EVENT_DRIVEN only)
4. **Team manifest injection** (inject `{{team}}` into prompts)
5. **Final agent config preparation** (context injection + tool format override)
6. **Coordinator initialization** (ensure coordinator starts early)

When complete, the worker enqueues `AgentTeamReadyEvent` and the phase transitions to IDLE.

---

## 7. Task Plan + Notification Modes
Teams can run in two modes (see `TaskNotificationMode`):

### 7.1 AGENT_MANUAL_NOTIFICATION (default)
- Coordinator explicitly sends messages to agents using tools.
- TaskPlan is updated, but no automatic activation occurs.

### 7.2 SYSTEM_EVENT_DRIVEN
- `SystemEventDrivenAgentTaskNotifier` monitors TaskPlan events.
- `ActivationPolicy` tracks which agents have already been activated for a “wave”.
- `TaskActivator` ensures the agent is running and sends a generic “start work” message.
- Runnable tasks are marked `QUEUED` before activation.

This mode allows *fully automated* task distribution with minimal coordinator overhead.

---

## 8. Inter-Agent Messaging
`send_message_to` is implemented as a tool. It:

- retrieves `team_context` injected into agent configs,
- uses `TeamManager` to dispatch `InterAgentMessageRequestEvent`,
- triggers on-demand startup for the recipient if needed.

This avoids direct agent-to-agent calls and keeps routing consistent.

---

## 9. Streaming + Observability
Agent Teams expose a unified stream via `AgentTeamExternalEventNotifier`:

- **TEAM**: phase transitions
- **AGENT**: re-broadcast agent events
- **SUB_TEAM**: re-broadcast sub-team streams
- **TASK_PLAN**: task plan updates

`AgentEventMultiplexer` manages bridges:

- `AgentEventBridge`: agent → team stream
- `TeamEventBridge`: sub-team → team stream

`AgentTeamEventStream` provides async consumption for UIs and dashboards.

---

## 10. Shutdown
`AgentTeamShutdownOrchestrator` runs inside the worker loop:

1. **Bridge cleanup** (stop event bridges)
2. **Sub-team shutdown**
3. **Agent shutdown**

This ensures the team fully tears down its resources and running nodes.

---

## 11. Key Files (Reference)
- Team facade: `autobyteus/agent_team/agent_team.py`
- Builder + config: `autobyteus/agent_team/agent_team_builder.py`, `autobyteus/agent_team/context/agent_team_config.py`
- Runtime + worker: `autobyteus/agent_team/runtime/agent_team_runtime.py`, `autobyteus/agent_team/runtime/agent_team_worker.py`
- TeamManager: `autobyteus/agent_team/context/team_manager.py`
- Bootstrap steps: `autobyteus/agent_team/bootstrap_steps/`
- Task notification: `autobyteus/agent_team/task_notification/`
- Streaming + multiplexer: `autobyteus/agent_team/streaming/`
- Shutdown steps: `autobyteus/agent_team/shutdown_steps/`

---

## 12. Extension Points
- **Custom team APIs**: subclass `BaseAgentTeam` to wrap `AgentTeam`.
- **Custom bootstrap steps**: pass new step lists to `AgentTeamBootstrapper`.
- **Task activation behavior**: override or replace `ActivationPolicy` / `TaskActivator`.
- **New stream payloads**: extend team stream payload definitions.

