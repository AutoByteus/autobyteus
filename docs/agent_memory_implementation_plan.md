# Agent Memory Implementation Plan

**Status:** Active
**Date:** 2026-01-30

This plan defines a **bottom-up implementation sequence** for the memory-centric
refactor. It lists dependencies, file touch points, and test checkpoints so we
can move step-by-step safely.

---

## 0) Ground Rules

- **Bottom-up**: build lowest-level primitives first.
- **No legacy paths**: remove LLM-owned history; memory is the only source of truth.
- **TDD**: add tests before or alongside each unit.
- **Small batches**: each step should be independently testable.

---

## Progress Tracker

- [x] Phase 1: Tool-aware `Message` model + tests
- [x] Phase 2: Extension refactor (explicit messages)
- [x] Phase 3: ActiveTranscript
- [x] Phase 4: Compaction Snapshot Builder
- [x] Phase 5: Prompt Renderers
- [x] Phase 6: Stateless LLM API
- [x] Phase 7: LLMRequestAssembler
- [x] Phase 8: Handler integration
- [x] Phase 9: Model defaults & token budgets
- [x] Phase 10: Cleanup/removal of legacy history

---

## 1) Completed Foundation

**Done**

- Tool-aware `Message` model with `tool_payload`.
- Unit tests for tool payload serialization.

Files:
- `autobyteus/llm/utils/messages.py`
- `tests/unit_tests/llm/utils/test_messages.py`

---

## 2) Extension Refactor (Token Usage)

**Goal**

Extensions operate on explicit messages and rendered payloads.

**Dependencies**

- `Message` model (done).

**Changes**

- Update `LLMExtension` interface to:
  - `before_invoke(messages, rendered_payload, **kwargs)`
  - `after_invoke(messages, response, **kwargs)`
- Update `TokenUsageTrackingExtension`:
  - Use explicit `messages` for token counts
  - Remove `on_user_message_added` / `on_assistant_message_added`

**Files**

- `autobyteus/llm/extensions/base_extension.py`
- `autobyteus/llm/extensions/token_usage_tracking_extension.py`
- `autobyteus/llm/utils/token_usage_tracker.py` (if needed)
- Tests:
  - `tests/integration_tests/llm/extensions/token_usage_tracking_extension/*`

**Test checkpoint**

- `.venv/bin/python -m pytest tests/integration_tests/llm/extensions/token_usage_tracking_extension -q`

---

## 3) Active Transcript (Memory Core)

**Goal**

Introduce `ActiveTranscript` as the canonical, append-only message list for the
current compaction epoch.

**Dependencies**

- Tool-aware `Message` model
- Token usage refactor (optional, but recommended to finish first)

**Changes**

- Add `autobyteus/memory/active_transcript.py`
  - `append_user`, `append_assistant`, `append_tool_calls`, `append_tool_result`
  - `reset(snapshot_messages)`
  - `build_messages()` (return list)
  - metadata: `epoch_id`, `last_compaction_ts`

**Tests**

- New: `tests/unit_tests/memory/test_active_transcript.py`
  - Append ordering
  - Reset behavior
  - Tool payload handling

**Test checkpoint**

- `.venv/bin/python -m pytest tests/unit_tests/memory/test_active_transcript.py -q`

---

## 4) Compaction Snapshot Builder

**Goal**

Deterministically build the compaction snapshot (system + episodic + semantic + raw tail).

**Dependencies**

- ActiveTranscript
- Retrieval bundle models

**Changes**

- Add `autobyteus/memory/compaction_snapshot_builder.py`
- Add deterministic formatting (stable ordering, no timestamps)

**Tests**

- `tests/unit_tests/memory/test_compaction_snapshot_builder.py`
  - Output ordering, stability

---

## 5) Prompt Renderer Layer

**Goal**

Provider-specific rendering for explicit message lists.

**Dependencies**

- Tool payload model
- ActiveTranscript (for message list)

**Changes**

- `autobyteus/llm/prompt_renderers/base_prompt_renderer.py`
- `autobyteus/llm/prompt_renderers/openai_responses_renderer.py`
- `autobyteus/llm/prompt_renderers/openai_chat_renderer.py`

**Tests**

- New unit tests per renderer:
  - `tests/unit_tests/llm/prompt_renderers/test_openai_responses_renderer.py`
  - `tests/unit_tests/llm/prompt_renderers/test_openai_chat_renderer.py`

**Test checkpoint**

- `.venv/bin/python -m pytest tests/unit_tests/llm/prompt_renderers -q`

---

## 6) Stateless LLM API

**Goal**

LLM executes only on explicit messages (no internal history).

**Dependencies**

- Prompt renderers
- Extension refactor

**Changes**

- Add `BaseLLM.stream_messages(messages, **kwargs)`
- Provider classes accept explicit `messages` and call renderers
- Remove internal message mutation in provider call paths

**Files**

- `autobyteus/llm/base_llm.py`
- `autobyteus/llm/api/openai_responses_llm.py`
- `autobyteus/llm/api/openai_compatible_llm.py`
- `autobyteus/llm/api/claude_llm.py`
- `autobyteus/llm/api/gemini_llm.py`
- `autobyteus/llm/api/ollama_llm.py`

**Tests**

- Update LLM unit tests to use explicit message lists
- Ensure no `self.messages` mutation

---

## 7) LLMRequestAssembler

**Goal**

Orchestrate Memory + Renderer + Token budget without coupling layers.

**Dependencies**

- ActiveTranscript
- Prompt renderers
- Stateless LLM API

**Changes**

- Add `autobyteus/agent/llm_request_assembler.py`
  - `prepare_request(processed_user_input)` -> RequestPackage
  - token estimation and compaction trigger
  - re-render on compaction

**Tests**

- `tests/unit_tests/agent/test_llm_request_assembler.py`
  - compaction trigger
  - snapshot reset + re-render

---

## 8) Handler Integration

**Goal**

Wire ActiveTranscript and LLMRequestAssembler into runtime flow.

**Dependencies**

- LLMRequestAssembler
- Stateless LLM API

**Changes**

- `LLMUserMessageReadyEventHandler` uses assembler
- Streaming parser output → `ActiveTranscript.append_tool_calls(...)`
- `ToolResultEventHandler` uses tool messages + continuation user message

**Tests**

- Update handler tests:
  - `tests/unit_tests/agent/handlers/test_llm_user_message_ready_event_handler.py`
  - `tests/unit_tests/agent/handlers/test_tool_result_event_handler.py`

---

## 9) Model Defaults & Token Budgets

**Goal**

Move token budget defaults into `LLMModel`.

**Changes**

- Add to `LLMModel`:
  - `max_context_tokens`
  - `default_compaction_ratio`
  - `default_safety_margin_tokens`
- Add optional overrides to `LLMConfig`

**Tests**

- `tests/unit_tests/llm/test_model_token_budget_defaults.py`

---

## 10) Cleanup / Removal

**Goal**

Remove legacy history and duplicate state.

**Changes**

- Remove `BaseLLM.messages` usage
- Remove `AgentRuntimeState.conversation_history` from LLM flow
- Remove LLMUserMessage from core execution paths

**Validation**

- Ensure all LLM invocations use explicit message lists
- Ensure memory is only transcript source
