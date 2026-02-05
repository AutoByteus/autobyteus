from dataclasses import dataclass
from typing import Optional

from autobyteus.memory.working_context_snapshot_serializer import WorkingContextSnapshotSerializer
from autobyteus.memory.compaction_snapshot_builder import CompactionSnapshotBuilder
from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


@dataclass
class WorkingContextSnapshotBootstrapOptions:
    max_episodic: int = 3
    max_semantic: int = 20
    raw_tail_turns: Optional[int] = None


class WorkingContextSnapshotBootstrapper:
    def __init__(
        self,
        working_context_snapshot_store: Optional[WorkingContextSnapshotStore] = None,
        snapshot_builder: Optional[CompactionSnapshotBuilder] = None,
    ) -> None:
        self.working_context_snapshot_store = working_context_snapshot_store
        self.snapshot_builder = snapshot_builder or CompactionSnapshotBuilder()

    def bootstrap(self, memory_manager, system_prompt: str, options: WorkingContextSnapshotBootstrapOptions) -> None:
        store = self._resolve_store(memory_manager)
        agent_id = self._resolve_agent_id(memory_manager, store)

        if store and agent_id and store.exists(agent_id):
            payload = store.read(agent_id)
            if payload and WorkingContextSnapshotSerializer.validate(payload):
                snapshot, _meta = WorkingContextSnapshotSerializer.deserialize(payload)
                memory_manager.reset_working_context_snapshot(snapshot.build_messages())
                return

        bundle = memory_manager.retriever.retrieve(
            max_episodic=options.max_episodic,
            max_semantic=options.max_semantic,
        )
        tail_turns = options.raw_tail_turns
        if tail_turns is None:
            policy = getattr(memory_manager, "compaction_policy", None)
            tail_turns = getattr(policy, "raw_tail_turns", 0) if policy else 0
        raw_tail = memory_manager.get_raw_tail(tail_turns or 0, exclude_turn_id=None)
        snapshot_messages = self.snapshot_builder.build(
            system_prompt=system_prompt,
            bundle=bundle,
            raw_tail=raw_tail,
        )
        memory_manager.reset_working_context_snapshot(snapshot_messages)

    def _resolve_store(self, memory_manager) -> Optional[WorkingContextSnapshotStore]:
        if self.working_context_snapshot_store is not None:
            return self.working_context_snapshot_store
        return getattr(memory_manager, "working_context_snapshot_store", None)

    def _resolve_agent_id(self, memory_manager, store: Optional[WorkingContextSnapshotStore]) -> Optional[str]:
        if store and getattr(store, "agent_id", None):
            return store.agent_id
        store_obj = getattr(memory_manager, "store", None)
        return getattr(store_obj, "agent_id", None)
