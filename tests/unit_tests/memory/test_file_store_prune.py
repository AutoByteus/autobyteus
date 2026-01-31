import time

from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.store.file_store import FileMemoryStore


def _make_trace(turn_id: str, seq: int) -> RawTraceItem:
    return RawTraceItem(
        id=f"rt_{turn_id}_{seq}",
        ts=time.time(),
        turn_id=turn_id,
        seq=seq,
        trace_type="user",
        content="hi",
        source_event="LLMUserMessageReadyEvent",
    )


def test_prune_raw_traces_keeps_specified_turns(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    store.add([_make_trace("turn_0001", 1), _make_trace("turn_0002", 1)])

    store.prune_raw_traces(keep_turn_ids={"turn_0002"}, archive=False)

    remaining = store.list_raw_trace_dicts()
    assert len(remaining) == 1
    assert remaining[0]["turn_id"] == "turn_0002"


def test_prune_raw_traces_archives_removed(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    store.add([_make_trace("turn_0001", 1), _make_trace("turn_0002", 1)])

    store.prune_raw_traces(keep_turn_ids={"turn_0002"}, archive=True)

    archive = store.read_archive_raw_traces()
    assert len(archive) == 1
    assert archive[0]["turn_id"] == "turn_0001"
