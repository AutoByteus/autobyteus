# Proposed Design Document

## Design Version

- Current Version: `v3`

## Revision History

| Version | Trigger | Summary Of Changes | Related Review Round |
| --- | --- | --- | --- |
| v1 | Initial draft | Introduced unified tool lifecycle model for Python agent runtime. | 1 |
| v2 | Review finding F-001/F-002 | Replaced approved-event execution path with explicit execute-event path and terminal lifecycle notifications. | 1 |
| v3 | Review finding F-003 | Finalized stream payload/type alignment and removed legacy auto-executing/approval event naming from in-scope modules. | 2 |

## Summary

Align Python tool-status and tool-lifecycle behavior with the cleaner TypeScript architecture by introducing a single execution event, explicit lifecycle notifications, and typed stream payloads for approval/execution phases.

## Goals

- Replace split/duplicated execution flow with one execution handler driven by one event type.
- Emit explicit lifecycle events: approval requested, approved, denied, execution started, execution succeeded, execution failed.
- Keep status update semantics aligned with lifecycle events and make tool-name propagation deterministic.
- Keep CLI/TUI stream consumers aligned with new lifecycle event payloads.

## Non-Goals

- Port all TypeScript tool functionality into Python.
- Redesign unrelated parser or memory features.
- Add compatibility shims for old tool lifecycle event names.

## Legacy Removal Policy (Mandatory)

- Policy: `No backward compatibility; remove legacy code paths.`
- Required action: remove `ApprovedToolInvocationEvent` execution path and remove `TOOL_INVOCATION_*` lifecycle naming in in-scope streaming/notifier modules.

## Requirements And Use Cases

- UC-001: Manual approval requested for a pending tool invocation.
- UC-002: Approved tool invocation proceeds to execution and emits execution-started event.
- UC-003: Denied tool invocation emits denied lifecycle event and continues via denied tool-result pathway.
- UC-004: Tool result handling emits terminal lifecycle event (success/failure) and updates LLM input pipeline.

## Codebase Understanding Snapshot (Pre-Design Mandatory)

| Area | Findings | Evidence (files/functions) | Open Unknowns |
| --- | --- | --- | --- |
| Entrypoints / Boundaries | Worker dispatch applies status then routes to event handlers. | `autobyteus/agent/events/worker_event_dispatcher.py:34`, `autobyteus/agent/factory/agent_factory.py:40` | None |
| Current Naming Conventions | Python currently uses mixed old/new names (`ApprovedToolInvocationEvent`, `TOOL_INVOCATION_AUTO_EXECUTING`). | `autobyteus/agent/events/agent_events.py:138`, `autobyteus/agent/streaming/events/stream_events.py:39` | None |
| Impacted Modules / Responsibilities | Tool lifecycle split across request/approval/approved/result handlers and status utilities. | `autobyteus/agent/handlers/*.py`, `autobyteus/agent/status/*.py` | None |
| Data / Persistence / External IO | Lifecycle outputs flow through notifier -> stream events -> CLI/TUI. | `autobyteus/agent/events/notifiers.py`, `autobyteus/agent/streaming/streams/agent_event_stream.py`, `autobyteus/cli/*` | None |

## Current State (As-Is)

- Auto-execute path executes directly in request handler.
- Approved flow uses `ApprovedToolInvocationEvent` and dedicated handler.
- Denied flow injects a direct LLM message instead of a denied tool-result lifecycle.
- Stream payload/event names use old `TOOL_INVOCATION_*` labels.

## Target State (To-Be)

- Introduce `ExecuteToolInvocationEvent` as the only execution event.
- Use one `ToolInvocationExecutionEventHandler` for both auto-executed and approved invocations.
- On denial, emit tool-denied lifecycle notification and enqueue denied `ToolResultEvent` (`is_denied=True`).
- Emit tool lifecycle payloads from request/approval/execution/result handlers consistently.
- Use stream event types/payload models aligned with `TOOL_APPROVAL_REQUESTED`, `TOOL_APPROVED`, `TOOL_DENIED`, `TOOL_EXECUTION_*`.

## Change Inventory (Delta)

| Change ID | Change Type (`Add`/`Modify`/`Rename/Move`/`Remove`) | Current Path | Target Path | Rationale | Impacted Areas | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| C-001 | Add | N/A | `autobyteus/agent/events/agent_events.py` (`ExecuteToolInvocationEvent`) | Unify tool execution trigger event. | Events, status, handlers | replaces approved execution trigger |
| C-002 | Remove | `autobyteus/agent/events/agent_events.py` (`ApprovedToolInvocationEvent`) | Removed | Eliminate legacy execution event. | Events, handlers, factory | hard removal |
| C-003 | Add | N/A | `autobyteus/agent/handlers/tool_lifecycle_payload.py` | Shared lifecycle payload builder. | Request/approval/execution/result handlers | mirror TS helper |
| C-004 | Add | N/A | `autobyteus/agent/handlers/tool_invocation_execution_event_handler.py` | Single execution handler for all execution paths. | Handler registry/factory | replaces approved handler runtime role |
| C-005 | Remove | `autobyteus/agent/handlers/approved_tool_invocation_event_handler.py` | Removed | Remove duplicate/legacy execution logic. | Factory, handlers exports | clean replacement |
| C-006 | Modify | `autobyteus/agent/handlers/tool_invocation_request_event_handler.py` | same | Request approval or enqueue execute event; no direct execution branch. | Tool invocation lifecycle | cleaner separation |
| C-007 | Modify | `autobyteus/agent/handlers/tool_execution_approval_event_handler.py` | same | Emit approved/denied lifecycle notifications and queue execute/denied-result event. | Approval lifecycle | denial no longer bypasses tool-result path |
| C-008 | Modify | `autobyteus/agent/handlers/tool_result_event_handler.py` | same | Handle denied results and emit execution success/failure lifecycle notifications. | Result lifecycle | status + stream clarity |
| C-009 | Modify | `autobyteus/agent/status/status_deriver.py`, `autobyteus/agent/status/status_update_utils.py` | same | Switch from approved event to execute event, keep refined status payload behavior. | Status projection | consistent tool_name reporting |
| C-010 | Modify | `autobyteus/events/event_types.py`, `autobyteus/agent/events/notifiers.py` | same | Replace old invocation event names with refined lifecycle names and notifier methods. | Event bus | no legacy aliases |
| C-011 | Modify | `autobyteus/agent/streaming/events/*.py`, `autobyteus/agent/streaming/streams/agent_event_stream.py` | same | Add/rename typed stream payloads and mappings for refined lifecycle events. | Stream typing | aligns with TS model |
| C-012 | Modify | `autobyteus/cli/*.py` and TUI widgets/state files | same | Consume and render refined lifecycle stream events. | User-facing logs/prompts | maintain UX behavior |

## Architecture Overview

`PendingToolInvocationEvent` now only decides approval vs execution scheduling. Actual execution moves to one handler (`ExecuteToolInvocationEvent`). Lifecycle notifications are emitted at phase boundaries and forwarded through typed stream events.

## File And Module Breakdown

| File/Module | Change Type | Concern / Responsibility | Public APIs | Inputs/Outputs | Dependencies |
| --- | --- | --- | --- | --- | --- |
| `autobyteus/agent/events/agent_events.py` | Modify | Event model for runtime flow | Dataclass events | in-memory events | handlers, status deriver |
| `autobyteus/agent/handlers/tool_invocation_request_event_handler.py` | Modify | Approval request vs execution enqueue | `handle` | pending invocation -> notify/enqueue | notifier, queues |
| `autobyteus/agent/handlers/tool_invocation_execution_event_handler.py` | Add | Tool execution orchestration | `handle` | execute event -> tool result event | preprocessors, notifier |
| `autobyteus/agent/handlers/tool_execution_approval_event_handler.py` | Modify | Approval decisions and lifecycle | `handle` | approval event -> execute/result events | runtime state, notifier |
| `autobyteus/agent/handlers/tool_result_event_handler.py` | Modify | Tool result processing + aggregation | `handle` | tool result -> user message + lifecycle | processors, notifier |
| `autobyteus/agent/status/*.py` | Modify | Status projection + additional payloads | `apply`, `build_status_update_data` | event -> status | event classes |
| `autobyteus/agent/events/notifiers.py` | Modify | External lifecycle event emission | `notify_*` methods | internal lifecycle -> event bus | `EventType` |
| `autobyteus/agent/streaming/events/*.py` | Modify | Typed stream payload model | payload classes/factories | event bus payload -> typed payload | CLI/TUI |
| `autobyteus/agent/streaming/streams/agent_event_stream.py` | Modify | Map event bus to stream events | `all_events`, convenience streams | notifier events -> stream events | payload factories |

## Naming Decisions (Natural And Implementation-Friendly)

| Item Type (`File`/`Module`/`API`) | Current Name | Proposed Name | Reason | Notes |
| --- | --- | --- | --- | --- |
| API | `ApprovedToolInvocationEvent` | `ExecuteToolInvocationEvent` | Name describes action boundary, not decision history. | Removes ambiguity |
| API | `notify_agent_request_tool_invocation_approval` | `notify_agent_tool_approval_requested` | Consistent lifecycle naming family. | matches TS naming |
| API | `notify_agent_tool_invocation_auto_executing` | `notify_agent_tool_execution_started` | Execution phase naming, not configuration detail naming. | cleaner UI semantics |
| Stream Type | `TOOL_INVOCATION_APPROVAL_REQUESTED` | `TOOL_APPROVAL_REQUESTED` | Align stream names with lifecycle terminology. | |
| Stream Type | `TOOL_INVOCATION_AUTO_EXECUTING` | `TOOL_EXECUTION_STARTED` | Distinguish start from completion/failure events. | |

## Dependency Flow And Cross-Reference Risk

| Module/File | Upstream Dependencies | Downstream Dependents | Cross-Reference Risk | Mitigation / Boundary Strategy |
| --- | --- | --- | --- | --- |
| `agent_events.py` | none | status + handlers + factory | Medium | update imports in same commit |
| `tool_invocation_execution_event_handler.py` | events + context + notifier | factory registry | Medium | introduce file before factory switch |
| `notifiers.py` + `event_types.py` | event emitter | stream mapper + UI | High | change mapping and payload classes in same patch set |
| CLI/TUI files | streaming payload/types | user interaction | Medium | update event condition branches + renderables together |

## Decommission / Cleanup Plan

| Item To Remove/Rename | Cleanup Actions | Legacy Removal Notes | Verification |
| --- | --- | --- | --- |
| `ApprovedToolInvocationEvent` | Remove dataclass, imports, handler registration and tests. | No compatibility alias. | `rg "ApprovedToolInvocationEvent" autobyteus tests` |
| `approved_tool_invocation_event_handler.py` | Remove file and exports. | No shim handler. | `rg "approved_tool_invocation_event_handler|ApprovedToolInvocationEventHandler" autobyteus tests` |
| `TOOL_INVOCATION_*` stream/event names | Replace enums, payload classes, mapping, consumers. | No parallel legacy stream names kept. | `rg "TOOL_INVOCATION_" autobyteus tests` |
| old notifier method names | Replace callsites with refined lifecycle names. | No alias methods. | `rg "notify_agent_request_tool_invocation_approval|notify_agent_tool_invocation_auto_executing" autobyteus tests` |

## Error Handling And Edge Cases

- Missing pending invocation ID on approval events: log and ignore stale approval.
- Missing tool instance: emit failed result and lifecycle failure event.
- Preprocessor failure: emit failed result event with error text.
- Duplicate/out-of-turn result events: keep existing guard behavior in result handler.
- Denied invocation: mark tool result as denied and avoid execution terminal lifecycle events.

## Use-Case Coverage Matrix (Design Gate)

| use_case_id | Use Case | Primary Path Covered (`Yes`/`No`) | Fallback Path Covered (`Yes`/`No`/`N/A`) | Error Path Covered (`Yes`/`No`/`N/A`) | Runtime Call Stack Section |
| --- | --- | --- | --- | --- | --- |
| UC-001 | Pending invocation requiring user approval | Yes | N/A | Yes | UC-001 |
| UC-002 | Pending invocation auto-exec / approved path to execution | Yes | N/A | Yes | UC-002 |
| UC-003 | Tool approval denied path | Yes | N/A | Yes | UC-003 |
| UC-004 | Tool result terminal lifecycle and LLM aggregation | Yes | Yes | Yes | UC-004 |

## Change Traceability To Implementation Plan

| Change ID | Implementation Plan Task(s) | Verification (Unit/Integration/Manual) | Status |
| --- | --- | --- | --- |
| C-001..C-005 | T-01, T-02, T-03 | unit tests for handlers/status/event model | Planned |
| C-006..C-009 | T-04, T-05 | unit tests for request/approval/result/status utilities | Planned |
| C-010..C-012 | T-06, T-07 | stream + CLI/TUI unit tests and targeted manual smoke | Planned |

## Design Feedback Loop Notes (From Review/Implementation)

| Date | Trigger (Review/File/Test/Blocker) | Design Smell | Design Update Applied | Status |
| --- | --- | --- | --- | --- |
| 2026-02-13 | Round 1 review | Execution ownership split across handlers | Introduced explicit execution handler boundary and removed approved-event branch from design. | Resolved |
| 2026-02-13 | Round 2 review | Stream naming mismatch with notifier lifecycle naming | Unified event type/payload naming to lifecycle family and removed invocation-auto naming. | Resolved |

## Open Questions

- None blocking for implementation.
