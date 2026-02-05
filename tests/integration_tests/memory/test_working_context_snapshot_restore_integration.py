import time

from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.memory.working_context_snapshot import WorkingContextSnapshot
from autobyteus.memory.working_context_snapshot_serializer import WorkingContextSnapshotSerializer
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.restore.working_context_snapshot_bootstrapper import (
    WorkingContextSnapshotBootstrapper,
    WorkingContextSnapshotBootstrapOptions,
)
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


def test_working_context_snapshot_restore_uses_cache(tmp_path):
    snapshot = WorkingContextSnapshot()
    snapshot.append_message(Message(role=MessageRole.SYSTEM, content="System"))
    snapshot.append_message(Message(role=MessageRole.USER, content="Hello"))

    payload = WorkingContextSnapshotSerializer.serialize(
        snapshot,
        {"schema_version": 1, "agent_id": "agent_cache"},
    )

    working_context_snapshot_store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id="agent_cache")
    working_context_snapshot_store.write("agent_cache", payload)

    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_cache")
    manager = MemoryManager(store=store, working_context_snapshot_store=working_context_snapshot_store)

    bootstrapper = WorkingContextSnapshotBootstrapper(working_context_snapshot_store=working_context_snapshot_store)
    bootstrapper.bootstrap(manager, system_prompt="System", options=WorkingContextSnapshotBootstrapOptions())

    messages = manager.get_working_context_messages()
    assert [m.role for m in messages] == [MessageRole.SYSTEM, MessageRole.USER]
    assert messages[1].content == "Hello"


def test_working_context_snapshot_restore_fallback_builds_snapshot(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_fallback")
    working_context_snapshot_store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id="agent_fallback")
    manager = MemoryManager(store=store, working_context_snapshot_store=working_context_snapshot_store)

    episodic = EpisodicItem(
        id="ep_1",
        ts=time.time(),
        turn_ids=["turn_0001"],
        summary="User asked about memory.",
        tags=[],
        salience=0.0,
    )
    semantic = SemanticItem(
        id="sem_1",
        ts=time.time(),
        fact="User prefers concise answers.",
        tags=[],
        confidence=0.9,
        salience=0.0,
    )
    raw_tail = RawTraceItem(
        id="rt_1",
        ts=time.time(),
        turn_id="turn_0002",
        seq=1,
        trace_type="user",
        content="Current question",
        source_event="LLMUserMessageReadyEvent",
    )
    store.add([episodic, semantic, raw_tail])

    bootstrapper = WorkingContextSnapshotBootstrapper(working_context_snapshot_store=working_context_snapshot_store)
    options = WorkingContextSnapshotBootstrapOptions(max_episodic=3, max_semantic=20, raw_tail_turns=1)
    bootstrapper.bootstrap(manager, system_prompt="System", options=options)

    messages = manager.get_working_context_messages()
    assert messages[0].role == MessageRole.SYSTEM
    assert messages[1].role == MessageRole.USER
    assert "[MEMORY:EPISODIC]" in messages[1].content
