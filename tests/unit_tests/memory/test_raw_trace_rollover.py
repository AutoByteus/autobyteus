import time

from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


class _Summarizer(Summarizer):
    def summarize(self, traces):
        return CompactionResult(episodic_summary="Summary", semantic_facts=[])


def _trace(turn_id: str, seq: int, trace_type: str = "user") -> RawTraceItem:
    return RawTraceItem(
        id=f"rt_{turn_id}_{seq}",
        ts=time.time(),
        turn_id=turn_id,
        seq=seq,
        trace_type=trace_type,
        content=f"{turn_id}:{seq}",
        source_event="LLMUserMessageReadyEvent",
    )


def test_raw_trace_rollover_after_compaction(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_rollover")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=_Summarizer())
    manager = MemoryManager(store=store, compaction_policy=policy, compactor=compactor)

    # Seed three turns
    store.add(
        [
            _trace("turn_0001", 1),
            _trace("turn_0002", 1),
            _trace("turn_0003", 1),
        ]
    )

    window = compactor.select_compaction_window()
    assert window == ["turn_0001", "turn_0002"]
    compactor.compact(window)

    # After compaction keep the tail turn only
    remaining = store.list_raw_trace_dicts()
    assert {item["turn_id"] for item in remaining} == {"turn_0003"}

    # New turn starts and appends new trace without conflicting sequence
    new_turn = manager.start_turn()
    assert new_turn != "turn_0003"
    manager.ingest_user_message(
        llm_user_message=type("Msg", (), {"content": "fresh", "image_urls": [], "audio_urls": [], "video_urls": []}),
        turn_id=new_turn,
        source_event="LLMUserMessageReadyEvent",
    )

    updated = store.list_raw_trace_dicts()
    assert {item["turn_id"] for item in updated} == {"turn_0003", new_turn}
