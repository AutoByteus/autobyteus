from unittest.mock import MagicMock

from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot
from autobyteus.memory.working_context_snapshot_serializer import WorkingContextSnapshotSerializer
from autobyteus.memory.restore.working_context_snapshot_bootstrapper import (
    WorkingContextSnapshotBootstrapper,
    WorkingContextSnapshotBootstrapOptions,
)
from autobyteus.memory.retrieval.memory_bundle import MemoryBundle


def test_bootstrapper_uses_cache_when_valid():
    snapshot = WorkingContextSnapshot()
    snapshot.append_message(Message(role=MessageRole.SYSTEM, content="System"))
    payload = WorkingContextSnapshotSerializer.serialize(
        snapshot,
        {"schema_version": 1, "agent_id": "agent_1"},
    )

    store = MagicMock()
    store.agent_id = "agent_1"
    store.exists.return_value = True
    store.read.return_value = payload

    memory_manager = MagicMock()
    memory_manager.reset_working_context_snapshot = MagicMock()
    memory_manager.retriever = MagicMock()
    memory_manager.get_raw_tail = MagicMock()

    bootstrapper = WorkingContextSnapshotBootstrapper(working_context_snapshot_store=store)
    bootstrapper.bootstrap(memory_manager, system_prompt="System", options=WorkingContextSnapshotBootstrapOptions())

    memory_manager.reset_working_context_snapshot.assert_called_once()
    memory_manager.retriever.retrieve.assert_not_called()


def test_bootstrapper_falls_back_to_rebuild_when_cache_missing():
    store = MagicMock()
    store.agent_id = "agent_1"
    store.exists.return_value = False

    memory_manager = MagicMock()
    memory_manager.reset_working_context_snapshot = MagicMock()
    memory_manager.retriever = MagicMock()
    memory_manager.retriever.retrieve.return_value = MemoryBundle(episodic=[], semantic=[])
    memory_manager.get_raw_tail.return_value = []
    memory_manager.compaction_policy = MagicMock(raw_tail_turns=4)

    snapshot_builder = MagicMock()
    snapshot_builder.build.return_value = [Message(role=MessageRole.SYSTEM, content="System")]

    bootstrapper = WorkingContextSnapshotBootstrapper(
        working_context_snapshot_store=store,
        snapshot_builder=snapshot_builder,
    )
    bootstrapper.bootstrap(memory_manager, system_prompt="System", options=WorkingContextSnapshotBootstrapOptions())

    snapshot_builder.build.assert_called_once()
    memory_manager.reset_working_context_snapshot.assert_called_once_with(snapshot_builder.build.return_value)
