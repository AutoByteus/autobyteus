# Implementation Plan (TDD, Bottom-Up)

## Phase 1: Low-Level Building Blocks
1. **WorkingContextSnapshotSerializer**
   - Write unit tests for serialize/deserialize/validate.
   - Implement serializer.

2. **WorkingContextSnapshotStore (file IO)**
   - Write unit tests for exists/read/write.
   - Implement store.

## Phase 2: Restore Orchestration (Memory Layer)
3. **WorkingContextSnapshotBootstrapper**
   - Unit tests for cache-hit and cache-miss paths.
   - Implement bootstrapper.

4. **MemoryManager persistence hooks**
   - Unit tests to confirm `persist_working_context_snapshot` is called on reset and assistant response.
   - Implement `persist_working_context_snapshot` and integrate hooks.

## Phase 3: Bootstrap Integration
5. **WorkingContextSnapshotRestoreStep**
   - Unit test: no-op without restore flag.
   - Unit test: calls bootstrapper when restore flag set.
   - Implement step and register in bootstrap sequence.

6. **AgentFactory.restore_agent**
   - Integration test: create memory cache, restore agent, ensure working context snapshot is loaded after bootstrap.
   - Implement factory restore path and runtime creation with existing `agent_id`.

## Phase 4: Integration Tests
7. **Integration: persistence + bootstrapper**
   - Use FileMemoryStore + WorkingContextSnapshotStore to write working context snapshot cache.
   - Ensure bootstrapper loads cache and restores working context snapshot.

8. **Integration: fallback rebuild**
   - No cache file; write episodic/semantic/raw tail.
   - Ensure bootstrapper builds snapshot and resets working context snapshot.
