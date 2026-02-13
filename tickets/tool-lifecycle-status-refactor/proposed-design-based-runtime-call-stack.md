# Proposed-Design-Based Runtime Call Stacks (Debug-Trace Style)

## Design Basis

- Scope Classification: `Medium`
- Call Stack Version: `v3`
- Source Artifact: `tickets/tool-lifecycle-status-refactor/proposed-design.md`
- Source Design Version: `v3`

## Use Case Index

- UC-001: Pending invocation requiring user approval.
- UC-002: Approved/auto invocation executes via unified execution event.
- UC-003: Denied invocation transitions via denied tool result.
- UC-004: Tool result settlement emits terminal lifecycle and aggregated LLM input.

## Use Case: UC-001 Pending Invocation Requiring User Approval

### Primary Runtime Call Stack

```text
[ENTRY] autobyteus/agent/events/worker_event_dispatcher.py:dispatch(PendingToolInvocationEvent)
├── [ASYNC] autobyteus/agent/status/status_update_utils.py:apply_event_and_derive_status(...)
│   ├── autobyteus/agent/status/status_deriver.py:_reduce(...)
│   │   └── [STATE] set status=AWAITING_TOOL_APPROVAL (auto_execute_tools=False)
│   └── autobyteus/agent/status/status_update_utils.py:build_status_update_data(...)
├── autobyteus/agent/handlers/tool_invocation_request_event_handler.py:handle(...)
│   ├── [STATE] autobyteus/agent/context/agent_runtime_state.py:store_pending_tool_invocation(...)
│   └── autobyteus/agent/events/notifiers.py:notify_agent_tool_approval_requested(...)
│       └── [ASYNC] autobyteus/agent/streaming/streams/agent_event_stream.py:_handle_notifier_event_sync(...)
└── autobyteus/cli/... consume StreamEventType.TOOL_APPROVAL_REQUESTED
```

### Error Path

```text
[ERROR] notifier unavailable while auto_execute_tools=False
autobyteus/agent/handlers/tool_invocation_request_event_handler.py:handle(...)
└── return without enqueueing execution path
```

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `N/A`
- Error Path: `Covered`

## Use Case: UC-002 Approved/Auto Invocation Executes Via Unified Execution Event

### Primary Runtime Call Stack

```text
[ENTRY-AUTO] autobyteus/agent/handlers/tool_invocation_request_event_handler.py:handle(...)
└── [ASYNC] autobyteus/agent/events/agent_input_event_queue_manager.py:enqueue_internal_system_event(ExecuteToolInvocationEvent)

[ENTRY-APPROVED] autobyteus/agent/handlers/tool_execution_approval_event_handler.py:handle(ToolExecutionApprovalEvent(is_approved=True))
├── [STATE] autobyteus/agent/context/agent_runtime_state.py:retrieve_pending_tool_invocation(...)
├── autobyteus/agent/events/notifiers.py:notify_agent_tool_approved(...)
└── [ASYNC] enqueue_internal_system_event(ExecuteToolInvocationEvent)

[EXECUTION] autobyteus/agent/events/worker_event_dispatcher.py:dispatch(ExecuteToolInvocationEvent)
├── [ASYNC] status_update_utils.apply_event_and_derive_status -> status=EXECUTING_TOOL
├── autobyteus/agent/handlers/tool_invocation_execution_event_handler.py:handle(...)
│   ├── preprocessor chain (optional)
│   ├── autobyteus/agent/events/notifiers.py:notify_agent_tool_execution_started(...)
│   ├── tool.execute(context=..., **arguments)
│   └── [ASYNC] enqueue_tool_result(ToolResultEvent)
└── [ASYNC] worker dispatch continues on ToolResultEvent
```

### Fallback / Error Paths

```text
[FALLBACK] preprocessor error
...tool_invocation_execution_event_handler.py:handle(...)
└── enqueue_tool_result(ToolResultEvent(error=...))
```

```text
[ERROR] tool instance missing or execute raises
...tool_invocation_execution_event_handler.py:handle(...)
└── enqueue_tool_result(ToolResultEvent(error=...))
```

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered`

## Use Case: UC-003 Denied Invocation Uses Denied Tool Result Path

### Primary Runtime Call Stack

```text
[ENTRY] autobyteus/agent/events/worker_event_dispatcher.py:dispatch(ToolExecutionApprovalEvent(is_approved=False))
├── [ASYNC] status_update_utils.apply_event_and_derive_status -> status=TOOL_DENIED
├── autobyteus/agent/handlers/tool_execution_approval_event_handler.py:handle(...)
│   ├── [STATE] retrieve_pending_tool_invocation(...)
│   ├── autobyteus/agent/events/notifiers.py:notify_agent_tool_denied(...)
│   └── [ASYNC] enqueue_tool_result(ToolResultEvent(is_denied=True,error=reason))
└── [ASYNC] worker dispatch handles ToolResultEvent next
```

### Error Path

```text
[ERROR] stale approval id
tool_execution_approval_event_handler.py:handle(...)
└── no pending invocation found -> return
```

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `N/A`
- Error Path: `Covered`

## Use Case: UC-004 Tool Result Emits Terminal Lifecycle And Aggregates For LLM

### Primary Runtime Call Stack

```text
[ENTRY] autobyteus/agent/events/worker_event_dispatcher.py:dispatch(ToolResultEvent)
├── [ASYNC] status_update_utils.apply_event_and_derive_status -> PROCESSING_TOOL_RESULT (if was EXECUTING_TOOL)
├── autobyteus/agent/handlers/tool_result_event_handler.py:handle(...)
│   ├── tool result processor chain (optional)
│   ├── autobyteus/agent/events/notifiers.py:notify_agent_data_tool_log(...)
│   ├── if not is_denied and error=None -> notify_agent_tool_execution_succeeded(...)
│   ├── if not is_denied and error!=None -> notify_agent_tool_execution_failed(...)
│   ├── settle single/multi-turn results [STATE]
│   └── [ASYNC] enqueue_user_message(UserMessageReceivedEvent(sender=TOOL))
└── next loop consumes aggregated user message path
```

### Fallback / Error Paths

```text
[FALLBACK] duplicate or unknown invocation id during multi-turn settlement
tool_result_event_handler.py:handle(...)
└── log + return without duplicate progression
```

```text
[ERROR] formatter/processor failure
tool_result_event_handler.py:handle(...)
└── keep event handling alive; continue with robust logging path
```

### Coverage Status

- Primary Path: `Covered`
- Fallback Path: `Covered`
- Error Path: `Covered`
