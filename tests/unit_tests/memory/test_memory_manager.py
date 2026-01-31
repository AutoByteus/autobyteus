from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore


def test_memory_manager_ingest_user_message(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    manager = MemoryManager(store=store)

    turn_id = manager.start_turn()
    user_message = LLMUserMessage(content="Hello memory")
    manager.ingest_user_message(user_message, turn_id=turn_id, source_event="LLMUserMessageReadyEvent")

    raw_items = store.list(manager.memory_types.RAW_TRACE)
    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.turn_id == turn_id
    assert raw.trace_type == "user"
    assert raw.content == "Hello memory"
    assert raw.source_event == "LLMUserMessageReadyEvent"

from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.events.agent_events import ToolResultEvent
from autobyteus.llm.utils.response_types import CompleteResponse


def test_memory_manager_ingest_tool_intent(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    manager = MemoryManager(store=store)

    turn_id = manager.start_turn()
    invocation = ToolInvocation(name="list_directory", arguments={"path": "src"}, id="call_1", turn_id=turn_id)
    manager.ingest_tool_intent(invocation)

    raw_items = store.list(manager.memory_types.RAW_TRACE)
    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.turn_id == turn_id
    assert raw.trace_type == "tool_call"
    assert raw.tool_name == "list_directory"


def test_memory_manager_ingest_tool_result(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    manager = MemoryManager(store=store)

    turn_id = manager.start_turn()
    event = ToolResultEvent(tool_name="list_directory", result=["a"], tool_invocation_id="call_1", turn_id=turn_id)
    manager.ingest_tool_result(event)

    raw_items = store.list(manager.memory_types.RAW_TRACE)
    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.turn_id == turn_id
    assert raw.trace_type == "tool_result"
    assert raw.tool_name == "list_directory"


def test_memory_manager_ingest_assistant_response(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    manager = MemoryManager(store=store)

    turn_id = manager.start_turn()
    response = CompleteResponse(content="Done.")
    manager.ingest_assistant_response(response, turn_id=turn_id, source_event="LLMCompleteResponseReceivedEvent")

    raw_items = store.list(manager.memory_types.RAW_TRACE)
    assert len(raw_items) == 1
    raw = raw_items[0]
    assert raw.turn_id == turn_id
    assert raw.trace_type == "assistant"
    assert raw.content == "Done."


def test_memory_manager_increments_seq_within_turn(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    manager = MemoryManager(store=store)

    turn_id = manager.start_turn()
    user_message = LLMUserMessage(content="First")
    manager.ingest_user_message(user_message, turn_id=turn_id, source_event="LLMUserMessageReadyEvent")

    invocation = ToolInvocation(name="list_directory", arguments={}, id="call_1", turn_id=turn_id)
    manager.ingest_tool_intent(invocation)

    raw_items = store.list(manager.memory_types.RAW_TRACE)
    seqs = [item.seq for item in raw_items]
    assert sorted(seqs) == [1, 2]

