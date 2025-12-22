# Bash Executor Service Design

## Architectural Overview

The next-generation `bash_executor` behaves as a managed terminal service that exposes full-duplex interaction with a persistent shell. Agents interact with it as they would with a human-operated terminal tab: they can run sequential commands, respond to interactive prompts, and keep background jobs alive between invocations.

The design spans four layers:

1. **Session API**: network-facing contract consumed by agents and orchestration services.
2. **Session Orchestrator**: lifecycle management for pseudo-terminal (PTY) backed shell sessions.
3. **Execution Runtime**: per-session components that drive the PTY, stream output, and enforce policy.
4. **Support Services**: logging, auditing, metrics, and policy enforcement that cross-cut all other layers.

```
┌──────────────────────────────────────────────────────────────┐
│                      Agent Integrations                      │
└───────────────▲──────────────────────────────────────────────┘
                │ Session API (gRPC/HTTP)
┌───────────────┴──────────────────────────────────────────────┐
│                   Session Orchestrator                       │
│  - SessionManager    - PolicyEngine    - ResourceMonitor      │
└───────────────▲──────────────▲────────▲──────────────────────┘
                │              │        │
┌───────────────┴──────────────┴────────┴──────────────────────┐
│                  Execution Runtime (per session)             │
│  - ShellProcess + PTY     - OutputStream      - CommandQueue  │
└───────────────▲──────────────────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────────────────────┐
│                 Host OS / Filesystem / Sandbox                │
└──────────────────────────────────────────────────────────────┘

Support services (metrics, tracing, auditing) wrap every layer.

## Component Responsibilities

- **SessionManager**
  - Create, lookup, and destroy shell sessions.
  - Assign unique `session_id`, track metadata (cwd, env, sandbox mode, policy flags, creation time).
  - Enforce per-agent limits: max sessions, max lifetime, idle timeout.

- **ShellProcess**
  - Launch `/bin/bash --login` (configurable) under a PTY that simulates an interactive terminal.
  - Propagate sandboxing (chroot/bind mounts, seccomp, network ACL) and environment overrides.
  - Expose handles for stdin (write), stdout/stderr (read), and control signals.

- **CommandQueue**
  - Serialize writes to the PTY to prevent overlapping input.
  - Surface queue state (empty, busy) to the API for back-pressure.
  - Support both full command submissions and raw keystream chunks.

- **OutputStream**
  - Continuously read PTY output into a ring buffer (bounded) and persistence log (optional).
  - Emit structured events: `{timestamp, payload, cursor_position?, exit_code?, prompt_detected?}`.
  - Provide replay from a `since_token` cursor with flow control and truncation markers.

- **PolicyEngine**
  - Validate requested operations (directory access, background processes, signals).
  - Enforce scoped resource limits (CPU, memory, wall-clock) and escalate violations.
  - Compute keep-alive strategy; trigger idle warnings and auto-close.

- **ResourceMonitor**
  - Track session subprocess tree; sample CPU/IO usage.
  - Surface metrics (`session_idle`, `process_count`, `long_running_flag`) for telemetry and tests.

- **AuditLogger**
  - Persist structured command/response history, signal usage, errors.
  - Allow filtered playback for debugging and security review.

## Session Lifecycle

1. **Create**: client calls `CreateSession`; SessionManager validates policy, spawns ShellProcess, seeds metadata, returns `session_id` plus initial prompt snapshot.
2. **Operate**: client alternates `SendInput` (commands, keystrokes) and `ReadOutput` (long-poll or streaming). Output tokens reference positions in the ring buffer.
3. **Maintain**: SessionManager runs idle checks; ResourceMonitor samples process tree; PolicyEngine may send `SessionEvent` notifications (e.g., idle warning).
4. **Close**: client calls `CloseSession` or timeout triggers auto-close. SessionManager sends `exit` or `SIGTERM`, waits grace period, escalates to `SIGKILL` if required, collects final logs, updates audit trail.

## API Specification

The service exposes a protobuf/gRPC interface (JSON over HTTP translation is possible) using the following RPCs:

### CreateSession

```
message CreateSessionRequest {
  string agent_id = 1;
  string initial_cwd = 2;
  map<string, string> environment = 3;
  SessionPolicy policy = 4;
}

message SessionPolicy {
  uint32 idle_timeout_seconds = 1;
  uint32 max_lifetime_seconds = 2;
  bool allow_background_processes = 3;
  bool inherit_agent_workspace = 4;
}

message CreateSessionResponse {
  string session_id = 1;
  string prompt = 2;
  SessionMetadata metadata = 3;
  OutputToken token = 4;
}
```

### SendInput

```
message SendInputRequest {
  string session_id = 1;
  bytes data = 2;                 // UTF-8 command or raw keystrokes
  repeated ControlAction actions = 3;
}

message ControlAction {
  enum Type {
    CTRL_C = 0;
    CTRL_D = 1;
    SIGINT = 2;
    SIGTERM = 3;
    SIGKILL = 4;
    RESIZE = 5;
  }
  Type type = 1;
  uint32 cols = 2;
  uint32 rows = 3;
}

message SendInputResponse {
  bool accepted = 1;
  string command_id = 2;          // optional correlation for audit/testing
  SessionState state = 3;
}
```

### ReadOutput

```
message ReadOutputRequest {
  string session_id = 1;
  OutputToken since = 2;
  uint32 max_bytes = 3;
  uint32 wait_timeout_ms = 4;     // 0 for immediate return, >0 for long-poll
}

message OutputChunk {
  string session_id = 1;
  OutputToken token = 2;
  bytes payload = 3;
  bool truncated = 4;
  optional uint32 exit_code = 5;
  optional PromptInfo prompt = 6;
}

message ReadOutputResponse {
  repeated OutputChunk chunks = 1;
  SessionState state = 2;
}
```

### GetSession

```
message GetSessionRequest { string session_id = 1; }

message GetSessionResponse {
  SessionMetadata metadata = 1;
  SessionState state = 2;
}
```

### CloseSession

```
message CloseSessionRequest {
  string session_id = 1;
  CloseMode mode = 2;             // GRACEFUL, FORCE
}

message CloseSessionResponse {
  SessionState final_state = 1;
  string summary = 2;
}
```

### SubscribeSessionEvents (optional streaming)

```
message SessionEvent {
  string session_id = 1;
  enum Type {
    IDLE_WARNING = 0;
    IDLE_TIMEOUT = 1;
    RESOURCE_THRESHOLD = 2;
    POLICY_VIOLATION = 3;
    SESSION_CLOSED = 4;
  }
  Type type = 2;
  string detail = 3;
}
```

## Key Interactions

### Interactive Command Flow

1. Agent calls `CreateSession` → receives `session_id`, prompt.
2. Agent submits `SendInput` with `ls\n`.
3. OutputStream emits data → agent polls `ReadOutput` with prior token until prompt detected.
4. Agent sends next command or closes session.

### Long-Running Process Flow

1. Agent runs `uvicorn main:app`.
2. Shell remains busy; OutputStream keeps streaming logs.
3. Agent may `ReadOutput` periodically. SessionState remains `RUNNING`.
4. To stop, agent sends `SendInput` with `ControlAction{CTRL_C}` or `kill`.

### Background Job Flow

1. Agent executes `python job.py &`.
2. Shell prompt returns; job continues in background.
3. ResourceMonitor tracks child process tree; PolicyEngine ensures background execution is permitted.
4. Agent can query `jobs` via additional commands or close the session; `CloseSession` ensures cleanup if policy requires.

### Idle Timeout Flow

1. Session idle beyond `idle_timeout_seconds`.
2. PolicyEngine emits `SessionEvent{IDLE_WARNING}`.
3. After grace period, SessionManager sends `exit` and closes the session, returning a final summary.

## Session State Model

```
enum SessionState {
  UNKNOWN = 0;
  RUNNING = 1;        // Shell alive, accepting input
  BUSY = 2;           // Command executing; prompt not yet returned
  IDLE = 3;           // No active commands; prompt visible
  CLOSING = 4;        // Close initiated; waiting for shell exit
  CLOSED = 5;         // Session terminated cleanly
  ERROR = 6;          // Unexpected failure
}
```

State transitions are initiated by the orchestrator in response to shell events, policy triggers, or client actions. Output events include the current state so clients can drive state machines deterministically in tests.

## Testing Strategy

### Unit Tests

- **SessionManager**: creation limits, metadata updates, idle timeout scheduling (use fake clock).
- **CommandQueue**: ordering guarantees, partial writes, concurrent callers.
- **OutputStream**: prompt detection, truncation behavior, token monotonicity, replay from token.
- **PolicyEngine**: permission checks (workspace directory enforcement, background job policy).
- **ResourceMonitor**: PID tree enumeration, long-running detection heuristics.

### Integration Tests

- **Happy Path**: create session, run command, read output, close gracefully.
- **Interactive Prompt**: run `python -i`, send commands, ensure prompt toggles.
- **Long-Running Process**: start `sleep 10`, verify `ReadOutput` streaming and `ControlAction` stops it.
- **Background Process Cleanup**: run `sleep 100 &`, close session with cleanup, ensure process terminated if policy disallows persistence.
- **Failure Handling**: inject shell crash, verify `SessionState.ERROR`, audit entries, and close behavior.
- **Reconnect Flow**: simulate service restart; ensure session metadata persists or recovery behavior matches policy.

Simulations leverage a PTY stub in tests to control shell output deterministically, enabling design-driven test harnesses without launching real shells when not necessary.

## Observability & Operations

- **Metrics**: `sessions_active`, `session_duration`, `command_latency`, `output_throughput`, `policy_violations`.
- **Logging**: structured log per session with correlation IDs (`session_id`, `command_id`), truncated payloads for privacy.
- **Tracing**: span per API call with child spans for shell interactions.
- **Alerts**: on high failure rates, orphaned processes, abnormal resource usage.

## Rollout Considerations

1. **Feature Flag**: gate the session-based executor behind configuration while keeping legacy `bash_executor` available.
2. **Compatibility Layer**: provide a shim that emulates single-command execution using the new session API for backwards compatibility.
3. **Migration Plan**: update agents gradually to exploit persistent sessions; document API changes.
4. **Operational Readiness**: rehearse recovery from crashed shells, ensure audit logs meet compliance needs.

## Open Questions

1. How should session ownership transfer when multiple orchestrators manage the same agent (e.g., HA deployment)?
2. Do we need per-command quasi-transactional semantics (e.g., auto-revert on failure) or is raw shell behavior sufficient?
3. What is the retention policy for session logs and background process outputs?
4. Should the service provide command-level sandboxing (e.g., `sudo` restrictions) beyond OS-level capabilities?

Resolving these items will refine the implementation plan and associated acceptance tests.

