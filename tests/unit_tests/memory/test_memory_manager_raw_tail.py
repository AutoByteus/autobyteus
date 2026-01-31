import time

from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.store.file_store import FileMemoryStore


def _trace(turn_id: str, seq: int, trace_type: str = "user", content: str = "") -> RawTraceItem:
    return RawTraceItem(
        id=f"rt_{turn_id}_{seq}",
        ts=time.time(),
        turn_id=turn_id,
        seq=seq,
        trace_type=trace_type,
        content=content,
        source_event="TestEvent",
    )


def test_memory_manager_get_raw_tail_orders_by_turn_and_seq(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_tail")
    manager = MemoryManager(store=store)

    store.add(
        [
            _trace("turn_0001", 1, "user", "t1 user"),
            _trace("turn_0001", 2, "assistant", "t1 assistant"),
            _trace("turn_0002", 1, "user", "t2 user"),
            _trace("turn_0003", 1, "user", "t3 user"),
            _trace("turn_0003", 2, "tool_call", ""),
        ]
    )

    tail_items = manager.get_raw_tail(tail_turns=2)
    assert [(item.turn_id, item.seq) for item in tail_items] == [
        ("turn_0002", 1),
        ("turn_0003", 1),
        ("turn_0003", 2),
    ]


def test_memory_manager_get_raw_tail_excludes_current_turn(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_tail")
    manager = MemoryManager(store=store)

    store.add(
        [
            _trace("turn_0001", 1, "user", "t1"),
            _trace("turn_0002", 1, "user", "t2"),
            _trace("turn_0003", 1, "user", "t3"),
        ]
    )

    tail_items = manager.get_raw_tail(tail_turns=2, exclude_turn_id="turn_0003")
    assert [(item.turn_id, item.seq) for item in tail_items] == [
        ("turn_0001", 1),
        ("turn_0002", 1),
    ]
