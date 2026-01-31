import time

from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.tool_interaction import ToolInteractionStatus
from autobyteus.memory.store.file_store import FileMemoryStore


def _trace(**kwargs) -> RawTraceItem:
    return RawTraceItem(
        id=kwargs.get("id", "rt_1"),
        ts=kwargs.get("ts", time.time()),
        turn_id=kwargs.get("turn_id", "turn_0001"),
        seq=kwargs.get("seq", 1),
        trace_type=kwargs["trace_type"],
        content=kwargs.get("content", ""),
        source_event=kwargs.get("source_event", "TestEvent"),
        tool_name=kwargs.get("tool_name"),
        tool_call_id=kwargs.get("tool_call_id"),
        tool_args=kwargs.get("tool_args"),
        tool_result=kwargs.get("tool_result"),
        tool_error=kwargs.get("tool_error"),
    )


def test_memory_manager_get_tool_interactions_filters_by_turn(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_tool")
    manager = MemoryManager(store=store)

    store.add(
        [
            _trace(
                trace_type="tool_call",
                turn_id="turn_0001",
                seq=1,
                tool_call_id="call_1",
                tool_name="search",
                tool_args={"q": "a"},
            ),
            _trace(
                trace_type="tool_result",
                turn_id="turn_0001",
                seq=2,
                tool_call_id="call_1",
                tool_name="search",
                tool_result={"ok": True},
            ),
            _trace(
                trace_type="tool_call",
                turn_id="turn_0002",
                seq=1,
                tool_call_id="call_2",
                tool_name="write_file",
                tool_args={"path": "a.txt"},
            ),
        ]
    )

    all_interactions = manager.get_tool_interactions()
    assert {interaction.tool_call_id for interaction in all_interactions} == {"call_1", "call_2"}

    turn_1_interactions = manager.get_tool_interactions(turn_id="turn_0001")
    assert len(turn_1_interactions) == 1
    interaction = turn_1_interactions[0]
    assert interaction.tool_call_id == "call_1"
    assert interaction.status == ToolInteractionStatus.SUCCESS

    turn_2_interactions = manager.get_tool_interactions(turn_id="turn_0002")
    assert len(turn_2_interactions) == 1
    assert turn_2_interactions[0].status == ToolInteractionStatus.PENDING
