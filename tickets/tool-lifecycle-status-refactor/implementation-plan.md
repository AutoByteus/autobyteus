# Implementation Plan

## Scope Classification

- Classification: `Medium`
- Reasoning: event model + handler orchestration + notifier/stream payload + CLI/TUI consumer changes across multiple layers.
- Workflow Depth: proposed design -> runtime call stack -> review (3 rounds) -> implementation plan -> progress tracking.

## Plan Maturity

- Current Status: `Ready For Implementation`
- Notes: runtime call stack review reached Round 3 with `Implementation can start: Yes`.

## Preconditions (Must Be True Before Finalizing This Plan)

- Runtime call stack review artifact exists: Yes
- All in-scope use cases reviewed: Yes
- No unresolved blocking findings: Yes
- Minimum review rounds satisfied: Yes (3)
- Final gate decision in review artifact is `Implementation can start: Yes`: Yes

## Runtime Call Stack Review Gate (Required Before Implementation)

| Round | Use Case | Call Stack Location | Review Location | Naming Naturalness | File/API Naming Clarity | Business Flow Completeness | Structure & SoC Check | Unresolved Blocking Findings | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | UC-001..UC-004 | `tickets/tool-lifecycle-status-refactor/proposed-design-based-runtime-call-stack.md` | `tickets/tool-lifecycle-status-refactor/runtime-call-stack-review.md` | Fail | Fail | Fail | Fail | Yes | Fail |
| 2 | UC-001..UC-004 | `tickets/tool-lifecycle-status-refactor/proposed-design-based-runtime-call-stack.md` | `tickets/tool-lifecycle-status-refactor/runtime-call-stack-review.md` | Pass | Pass | Pass | Pass | Yes | Fail |
| 3 | UC-001..UC-004 | `tickets/tool-lifecycle-status-refactor/proposed-design-based-runtime-call-stack.md` | `tickets/tool-lifecycle-status-refactor/runtime-call-stack-review.md` | Pass | Pass | Pass | Pass | No | Pass |

## Go / No-Go Decision

- Decision: `Go`
- Evidence:
  - Review rounds completed: 3
  - Final review round: 3
  - Final review gate line: `Implementation can start: Yes`

## Principles

- Bottom-up dependency order.
- Test-driven updates for event/status/handler behavior.
- Mandatory modernization rule: no backward-compatibility shims in in-scope modules.

## Dependency And Sequencing Map

| Order | File/Module | Depends On | Why This Order |
| --- | --- | --- | --- |
| 1 | `autobyteus/agent/events/agent_events.py`, `autobyteus/events/event_types.py` | N/A | Core type contracts must exist first. |
| 2 | `autobyteus/agent/events/notifiers.py`, `autobyteus/agent/handlers/tool_lifecycle_payload.py` | event types | Lifecycle emission helpers next. |
| 3 | `autobyteus/agent/handlers/tool_invocation_execution_event_handler.py` | execute event + payload helper | New execution boundary before rewiring callers. |
| 4 | request/approval/result handlers + status utilities | steps 1-3 | Behavior rewrite and status alignment. |
| 5 | factory/exports + streaming payload/mapping | steps 1-4 | Wire runtime and typed stream model. |
| 6 | CLI/TUI consumers | stream schema | Keep UI handling coherent. |
| 7 | tests | all | Validate final behavior and cleanup. |

## Design Delta Traceability (Required For `Medium/Large`)

| Change ID (from proposed design doc) | Change Type | Planned Task ID(s) | Includes Remove/Rename Work | Verification |
| --- | --- | --- | --- | --- |
| C-001..C-005 | Add/Remove | T-01, T-02, T-03 | Yes | unit tests for events/factory/handlers |
| C-006..C-009 | Modify | T-04, T-05 | No | unit tests for handlers/status |
| C-010..C-012 | Modify | T-06, T-07 | Yes | stream + CLI/TUI tests |

## Decommission / Rename Execution Tasks

| Task ID | Item | Action (`Remove`/`Rename`/`Move`) | Cleanup Steps | Risk Notes |
| --- | --- | --- | --- | --- |
| T-DEL-001 | `ApprovedToolInvocationEvent` + handler | Remove | delete event/handler/imports/registration/tests | medium risk: broad references |
| T-DEL-002 | `TOOL_INVOCATION_*` stream naming | Rename/Remove | replace enum/payload/mappings and UI checks | medium risk: UI event filtering |

## Step-By-Step Plan

1. Introduce/refine lifecycle event types and notifier APIs; add payload helper module.
2. Add execution-event handler and switch request/approval/status logic to execute-event model.
3. Refactor denial path to denied tool-result path and update result handler terminal lifecycle notifications.
4. Replace stream payload/type naming with refined lifecycle naming and update stream mapper.
5. Update CLI/TUI consumers and factory wiring; remove approved handler path.
6. Update/extend unit tests and run targeted suites.

## Per-File Definition Of Done

| File | Implementation Done Criteria | Unit Test Criteria | Integration Test Criteria | Notes |
| --- | --- | --- | --- | --- |
| `autobyteus/agent/events/agent_events.py` | execute-event exists and approved-event removed | event/status tests updated | N/A | |
| `autobyteus/agent/handlers/tool_invocation_execution_event_handler.py` | handles preprocess/execute/error/notify/result enqueue | handler tests cover success/not-found/error/preprocessor-fail | flow integration smoke | |
| `autobyteus/agent/handlers/tool_execution_approval_event_handler.py` | approved/denied notifications + enqueue behavior updated | approval handler tests pass | roundtrip integration smoke | |
| `autobyteus/agent/streaming/events/*.py` | refined lifecycle payloads and factory methods in place | stream payload tests pass | stream event flow smoke | |
| `autobyteus/cli/*.py` and TUI files | refined stream event names handled | focused UI state/render tests | manual CLI/TUI smoke | |

## Test Strategy

- Unit tests:
  - `tests/unit_tests/agent/status/test_status_update_utils.py`
  - `tests/unit_tests/agent/handlers/test_tool_invocation_request_event_handler.py`
  - `tests/unit_tests/agent/handlers/test_tool_execution_approval_event_handler.py`
  - `tests/unit_tests/agent/handlers/test_tool_invocation_execution_event_handler.py` (new)
  - `tests/unit_tests/agent/streaming/events/test_stream_event_payloads.py`
  - `tests/unit_tests/agent/streaming/streams/test_agent_event_stream.py`
- Integration tests:
  - `tests/integration_tests/agent/test_full_tool_roundtrip_flow.py`
