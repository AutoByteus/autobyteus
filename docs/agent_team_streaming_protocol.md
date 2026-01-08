# Agent Team Streaming Protocol

**Date:** 2026-01-06  
**Status:** Implemented  
**Scope:** Agent Teams (Runtime, Streaming, Multiplexing)

## 1. Overview

Agent Teams in Autobyteus expose a **single, unified event stream** (`AgentTeamEventStream`) that acts as a multiplexer for all activity within the team. This stream aggregates events from:

1.  **TEAM**: The coordinator itself (status updates).
2.  **AGENT**: Individual agents running in the team (streamed responses, tool calls).
3.  **SUB_TEAM**: Nested sub-teams (recursive aggregation).
4.  **TASK_PLAN**: Task management events (task creation, status updates).

This document defines the **JSON wire format** and **data flow** for this stream.

---

## 2. Data Flow Architecture

The journey of an event from an individual agent to the final team stream involves three stages:

### Stage 1: Source (Agent Emission)

- **Component**: `AgentEventStream` (inside the Agent's runtime).
- **Action**: The agent emits a raw `StreamEvent` (e.g., a `SEGMENT_EVENT` from the streaming parser).
- **Payload**: A concise, agent-centric object.
  ```python
  StreamEvent(
      event_type="segment_event",
      agent_id="researcher_1",
      data={...}
  )
  ```

### Stage 2: Bridge (Multiplexing)

- **Component**: `AgentEventBridge` (managed by `AgentEventMultiplexer`).
- **Action**: Development of a dedicated bridge task for each agent.
- **Process**: The bridge consumes the `StreamEvent` and forwards it to the team's central notifier.

### Stage 3: Sink (Team Notification)

- **Component**: `AgentTeamExternalEventNotifier`.
- **Action**: Wraps the original `StreamEvent` into an **envelope** (`AgentTeamStreamEvent`) that identifies the source category (`AGENT`, `TEAM`, etc.).
- **Result**: The final JSON object sent over WebSocket.

---

## 3. JSON Protocol Specification

The top-level object for every message in the team stream is the `AgentTeamStreamEvent`.

### 3.1 Envelope Structure

```json
{
  "event_id": "uuid-string-1234",
  "timestamp": "2026-01-06T12:00:00Z",
  "team_id": "team-primary",
  "event_source_type": "TEAM | AGENT | SUB_TEAM | TASK_PLAN",
  "data": { ... } // Payload depends on event_source_type
}
```

### 3.2 Payload Schemas

#### A. Source Type: `TEAM`

Used for status updates of the team coordinator itself.

- **Python Class**: `AgentTeamStatusUpdateData`
- **Payload (`data`)**:
  ```json
  {
    "new_status": "IDLE", // Enum: IDLE, RUNNING, PAUSED, ERROR, SHUTTING_DOWN
    "old_status": "STARTING", // Optional
    "error_message": null // Optional string
  }
  ```

#### B. Source Type: `AGENT`

Multiplexed events from member agents.

- **Python Class**: `AgentEventRebroadcastPayload`
- **Payload (`data`)**:
  ```json
  {
    "agent_name": "Researcher_1", // Friendly node name from Team Configuration
    "agent_event": {
      // The original StreamEvent from the agent
      "event_id": "evt-5678",
      "timestamp": "...",
      "agent_id": "agent-uuid-001", // The agent's internal UUID
      "event_type": "segment_event",
      "data": {
        "type": "SEGMENT_CONTENT",
        "payload": { "delta": "Analysis " }
      }
    }
  }
  ```
  > **Note**: The nested `agent_event` preserves the full fidelity of the original agent stream, including the `agent_id`.

#### C. Source Type: `SUB_TEAM`

Recursive events from nested teams.

- **Python Class**: `SubTeamEventRebroadcastPayload`
- **Payload (`data`)**:
  ```json
  {
    "sub_team_node_name": "backend_team",
    "sub_team_event": { ... } // Recursive AgentTeamStreamEvent
  }
  ```

#### D. Source Type: `TASK_PLAN`

Events related to the shared task board.

- **Python Class**: `TaskPlanEventPayload` (Union)
- **Payload (`data`)** (Example: `TasksCreatedEvent`):
  ```json
  {
    "tasks": [{ "id": "t1", "description": "Research protocol" }]
  }
  ```

---

## 4. Class Reference

| JSON Field         | Python Class                     | File Location                                              |
| :----------------- | :------------------------------- | :--------------------------------------------------------- |
| **Envelope**       | `AgentTeamStreamEvent`           | `agent_team/streaming/agent_team_stream_events.py`         |
| **`data` (AGENT)** | `AgentEventRebroadcastPayload`   | `agent_team/streaming/agent_team_stream_event_payloads.py` |
| **`data` (TEAM)**  | `AgentTeamStatusUpdateData`      | `agent_team/streaming/agent_team_stream_event_payloads.py` |
| **`reader`**       | `AgentTeamExternalEventNotifier` | `agent_team/streaming/agent_team_event_notifier.py`        |

---

## 5. Wire Protocol (WebSocket)

**Note:** The JSON structure described above is the **internal server-side protocol**. Before being sent over the WebSocket to the frontend, these events are **flattened** by the `AgentTeamStreamHandler`.

### Transformation Logic (`AgentTeamStreamHandler`)

When an `AGENT` event (`AgentEventRebroadcastPayload`) is processed:

1.  The inner `agent_event` is extracted.
2.  It is converted to a standard `ServerMessage` (same as single-agent mode).
3.  The `agent_name` (friendly node name) and `agent_id` (unique instance ID) are **injected** into the top-level payload.

### Final Client-Side JSON Example

```json
{
  "type": "SEGMENT_CONTENT",
  "payload": {
    "id": "seg_uuid_1",
    "segment_type": "text",
    "delta": "Hello world",
    "agent_name": "Researcher_1", // Injected by handler
    "agent_id": "agent-123" // Injected by handler
  }
}
```

This flattening ensures that the frontend can reuse existing single-agent components while simply checking for the extra `agent_name` field to attribute the activity.
