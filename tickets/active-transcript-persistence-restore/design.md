# Working Context Snapshot Persistence + Restore

## Goal
Persist a derived Working Context Snapshot cache so agent restore can be fast and deterministic. If the cache is missing or invalid, rebuild from memory (episodic/semantic/raw tail) and system prompt.

## Non-Goals
- Perfect replay of in-flight execution (queues, pending tool calls, streaming state)
- Replacing memory store as the source of truth
- Changing compaction policy or memory retrieval strategy

## Design Summary
- Treat Working Context Snapshot as a **cache**.
- Persist to `memory/agents/<agent_id>/working_context_snapshot.json`.
- On restore, **prefer cache** if valid; otherwise rebuild via Compaction Snapshot.
- Restore runs inside bootstrap via a **restore-only** `WorkingContextSnapshotRestoreStep` gated by `restore_options`.
- Keep persistence and restore logic separate from agent runtime and memory store.

---

## Files and Responsibilities

### 1) `autobyteus/memory/working_context_snapshot_serializer.py` (new)
**Responsibility:** Pure serialization/deserialization of `WorkingContextSnapshot` and `Message` objects.

**APIs:**
- `serialize(working_context_snapshot: WorkingContextSnapshot, metadata: dict) -> dict`
  - Converts working context snapshot + metadata to JSON-serializable dict.
- `deserialize(payload: dict) -> tuple[WorkingContextSnapshot, dict]`
  - Builds `WorkingContextSnapshot` + returns metadata.
- `validate(payload: dict) -> bool`
  - Checks schema version, required fields, message structure.

**Notes:**
- Must support tool payloads (tool calls/results), media URLs, reasoning.
- Include `schema_version` for future upgrades.

---

### 2) `autobyteus/memory/store/working_context_snapshot_store.py` (new)
**Responsibility:** File IO only for working context snapshot cache.

**APIs:**
- `exists(agent_id: str) -> bool`
- `read(agent_id: str) -> dict | None`
- `write(agent_id: str, payload: dict) -> None`

**Storage Path:**
- `memory/agents/<agent_id>/working_context_snapshot.json`

---

### 3) `autobyteus/memory/restore/working_context_snapshot_bootstrapper.py` (new)
**Responsibility:** Restore strategy (cache-first, fallback to rebuild).

**APIs:**
- `bootstrap(memory_manager: MemoryManager, system_prompt: str, options: WorkingContextSnapshotBootstrapOptions) -> None`

**Behavior:**
1. If cache exists and is valid:
   - Deserialize and `memory_manager.reset_working_context_snapshot(messages)`.
2. Else:
   - `Retriever.retrieve(max_episodic, max_semantic)`
   - `memory_manager.get_raw_tail(raw_tail_turns)`
   - `CompactionSnapshotBuilder.build(system_prompt, bundle, raw_tail)`
   - `memory_manager.reset_working_context_snapshot(snapshot)`

**Options (internal defaults):**
- `max_episodic`, `max_semantic`
- `raw_tail_turns` (override compaction policy if set)

---

### 4) `autobyteus/memory/memory_manager.py` (minor changes)
**Responsibility:** Trigger persistence at safe boundaries.

**Add:**
- `persist_working_context_snapshot()`
  - Uses `WorkingContextSnapshotSerializer` + `WorkingContextSnapshotStore`.

**Call sites:**
- After `reset_working_context_snapshot(...)` (compaction snapshot applied)
- After `ingest_assistant_response(...)` (end of turn)

---

### 4.1) `autobyteus/agent/context/agent_runtime_state.py` (update)
**Responsibility:** Carry restore intent through bootstrap.

**Add:**
- `restore_options: Optional[WorkingContextSnapshotBootstrapOptions] = None`

**Notes:**
- Set by `AgentFactory.restore_agent(...)`.
- Read by `WorkingContextSnapshotRestoreStep` to decide whether to run.

---

### 5) `autobyteus/agent/bootstrap_steps/working_context_snapshot_restore_step.py` (new)
**Responsibility:** Restore working context snapshot during bootstrap when in restore mode.

**APIs:**
- `execute(context: AgentContext) -> bool`

**Behavior:**
- Checks `context.state.restore_options` (or similar flag).
- If missing: no-op (normal agent start).
- If present: call `WorkingContextSnapshotBootstrapper.bootstrap(...)` using processed system prompt.

---

### 6) `autobyteus/agent/factory/agent_factory.py` (update)
**Responsibility:** Add a restore entrypoint on the factory.

**APIs:**
- `restore_agent(agent_id: str, config: AgentConfig, memory_dir: Optional[str] = None) -> Agent`

**Behavior:**
1. Create runtime with the **existing agent_id** (new internal helper, e.g. `_create_runtime_with_id`).
2. Initialize `MemoryManager` with `FileMemoryStore(base_dir, agent_id)`.
3. Set `runtime_state.restore_options` so `WorkingContextSnapshotRestoreStep` runs during bootstrap.
4. Return `Agent` (caller can `start()` or auto-start as desired).

---

## API Contracts (Behavior)

### `restore_agent(...)` (factory-level)
- Must use **same agent_id** to locate memory files.
- System prompt is rebuilt via existing bootstrap processors.
- Working context snapshot restore happens in `WorkingContextSnapshotRestoreStep` (cache-first, fallback rebuild).
- Does **not** restore runtime queues or in-flight tool executions.

### Working Context Snapshot Cache Validity
- Cache is considered valid if:
  - `schema_version` matches
  - `agent_id` matches
  - `messages` array is well-formed

On invalid cache, fallback to rebuild.

---

## Data Format (working_context_snapshot.json)
Suggested structure:
```
{
  "schema_version": 1,
  "agent_id": "agent_123",
  "epoch_id": 4,
  "last_compaction_ts": 1738100000.0,
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "...", "reasoning_content": "..."},
    {"role": "tool", "tool_payload": {...}}
  ]
}
```

---

## Why This Separation Works
- **Serializer**: pure data mapping, no IO.
- **Store**: pure IO, no logic.
- **Bootstrapper**: restore strategy only.
- **MemoryManager**: triggers persistence, stays memory-focused.
- **AgentFactory.restore_agent**: construction-only; bootstrap executes restore in the normal lifecycle.

---

## Open Questions
- Should we store the full processed system prompt in the cache, or only its hash?
- How often should we persist (every turn vs. only after compaction + assistant response)?
- Do we want a manual “rebuild working context snapshot” utility for maintenance?
