# AutoByteus Architecture Design Document

## 1. System Overview
AutoByteus is an event-driven, hierarchical multi-agent framework designed for asynchronous collaboration. It allows agents to operate concurrently, communicate via message passing, and manage complex projects through a shared Task Plan.

The core design philosophy separates **Execution** (Agents running in threads) from **Coordination** (Event-driven message routing).

---

## 2. Runtime Architecture (Concurrency)

### 2.1 The Threading Model
Unlike many sequential agent frameworks, AutoByteus agents run **in parallel**.

*   **One Agent = One Thread:** Every `Agent` instance (and the `TeamManager`) spins up its own dedicated thread upon startup.
*   **Event Loops:** Inside this dedicated thread, the agent runs its own `asyncio` event loop.
*   **Non-Blocking:** An agent waiting for an LLM response or executing a tool does **not** block other agents. Agent A can be generating code while Agent B is reviewing a file.

### 2.2 The Event Pipeline
Communication handles are asynchronous and queue-based:
1.  **Input Queues:** Every agent has an `AgentInputEventQueueManager` containing thread-safe queues (e.g., `user_message_queue`, `internal_system_event_queue`).
2.  **Worker Loop:** The `AgentWorker` continuously polls these queues in its private thread.
3.  **Dispatch:** Events are popped from the queue and routed to specific handlers (e.g., `ProcessUserMessageEventHandler`).

---

## 3. Team Architecture

### 3.1 The Team Manager
The `TeamManager` is the central router for a group of agents.
*   It maintains a registry of all active nodes (Agents and Sub-Teams).
*   It handles **On-Demand Startup**: If a message is sent to an agent that is currently sleeping or uninitialized, the Team Manager automatically starts that agent's thread before delivering the message.

### 3.2 Routing
Messages are not direct function calls between objects. They are events dispatched to the Team Manager, which then routes them to the recipient's input queue. This decoupling ensures stability even if the recipient is busy or restarting.

---

## 4. Task Management & Notification Modes

This is a critical architectural distinction that defines how work is distributed. The system supports two distinct workflows for task execution.

### 4.1 The Two Workflows

| Workflow | **Direct (Conversation-Driven)** | **Asynchronous (System-Driven)** |
| :--- | :--- | :--- |
| **Concept** | "I am telling you to do this." | "I am putting this on the board." |
| **Primary Tool** | `assign_task_to` | `create_tasks` |
| **Trigger** | The **Sender Agent** explicitly sends a notification message. | The **System** (TaskNotifier) detects a new runnable task. |
| **Dependency** | None. Works out of the box. | Requires `TaskNotificationMode.SYSTEM_EVENT_DRIVEN`. |

### 4.2 Task Notification Mode
The `TaskNotificationMode` attribute in `AgentTeamConfig` acts as a "Style Selector" for the team.
You can also set the default globally via `AUTOBYTEUS_TASK_NOTIFICATION_MODE` (`agent_manual_notification` or `system_event_driven`).

*   **`AGENT_MANUAL_NOTIFICATION` (Default)**
    *   **Behavior:** The system is passive. It maintains the Task Plan but never interrupts agents.
    *   **Use Case:** Teams that prefer high-context chat. The Manager assigns a task and adds specific verbal instructions ("Do this, but be careful of X").
    *   **Risk:** If a Manager creates a task but forgets to tell the worker, the worker stays idle.

*   **`SYSTEM_EVENT_DRIVEN`**
    *   **Behavior:** The system is active. A background component (`SystemEventDrivenAgentTaskNotifier`) watches the Task Plan.
    *   **Mechanism:** When `TASKS_CREATED` is emitted, the Notifier wakes up the assigned agent and sends a generic "You have work" message.
    *   **Use Case:** Bulk processing, automated pipelines, or "fire-and-forget" task creation using `create_tasks`.

---

## 5. Tooling Implementation Details

### 5.1 `assign_task_to` (Direct)
This tool performs two atomic actions sequentially:
1.  **Write:** Adds the task to the `TaskPlan`.
2.  **Notify:** Constructs and dispatches an `InterAgentMessageRequestEvent` to the assignee.
*   **Result:** The assignee is guaranteed to be notified immediately by the sender.

### 5.2 `create_tasks` (Async)
This tool performs only one action:
1.  **Write:** Adds the tasks to the `TaskPlan`.
*   **Result:** The tool finishes. No message is sent.
*   **Reaction:** If System Mode is ON, the Notifier detects the change and acts as the messenger. If System Mode is OFF, the tasks sit quietly until someone manually claims them.

### 5.3 `send_message_to`
This is the generic communication primitive. Like `assign_task_to`, it triggers the Team Manager's routing logic, ensuring the recipient is awake and ready to process the text.

---

## 6. Summary for Developers

*   **Concurrency:** You don't need to manage threads. Just create Agents; the runtime handles the parallelism.
*   **Task Assignment:**
    *   Use `assign_task_to` if you want your agents to "talk" about the work.
    *   Use `create_tasks` + `SYSTEM_EVENT_DRIVEN` if you want a "Project Manager" system to handle distribution automatically.
