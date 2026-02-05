from autobyteus.llm.utils.messages import Message, MessageRole
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.store.working_context_snapshot_store import WorkingContextSnapshotStore


def test_memory_manager_persists_on_reset(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_persist")
    working_context_snapshot_store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id="agent_persist")
    manager = MemoryManager(store=store, working_context_snapshot_store=working_context_snapshot_store)

    snapshot = [Message(role=MessageRole.SYSTEM, content="System")]
    manager.reset_working_context_snapshot(snapshot)

    payload = working_context_snapshot_store.read("agent_persist")
    assert payload is not None
    assert payload["messages"][0]["role"] == "system"


def test_memory_manager_persists_after_assistant_response(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_persist")
    working_context_snapshot_store = WorkingContextSnapshotStore(base_dir=tmp_path, agent_id="agent_persist")
    manager = MemoryManager(store=store, working_context_snapshot_store=working_context_snapshot_store)

    snapshot = [Message(role=MessageRole.SYSTEM, content="System")]
    manager.reset_working_context_snapshot(snapshot)

    turn_id = manager.start_turn()
    response = CompleteResponse(content="Hello", reasoning=None)
    manager.ingest_assistant_response(response, turn_id=turn_id, source_event="LLMCompleteResponseReceivedEvent")

    payload = working_context_snapshot_store.read("agent_persist")
    roles = [msg["role"] for msg in payload["messages"]]
    assert roles == ["system", "assistant"]
