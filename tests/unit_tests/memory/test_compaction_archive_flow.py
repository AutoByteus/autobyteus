import time

from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


class _Summarizer(Summarizer):
    def summarize(self, traces):
        return CompactionResult(
            episodic_summary="Archived summary",
            semantic_facts=[{"fact": "Keep this", "confidence": 0.8}],
        )


def _trace(turn_id: str, seq: int) -> RawTraceItem:
    return RawTraceItem(
        id=f"rt_{turn_id}_{seq}",
        ts=time.time(),
        turn_id=turn_id,
        seq=seq,
        trace_type="user",
        content=f"{turn_id} message",
        source_event="LLMUserMessageReadyEvent",
    )


def test_compaction_archives_pruned_raw_traces(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_archive")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=_Summarizer())

    store.add([_trace("turn_0001", 1), _trace("turn_0002", 1)])

    result = compactor.compact(["turn_0001"])
    assert result is not None

    remaining = store.list_raw_trace_dicts()
    assert {item["turn_id"] for item in remaining} == {"turn_0002"}

    archived = store.read_archive_raw_traces()
    assert {item["turn_id"] for item in archived} == {"turn_0001"}

    episodic = store.list(compactor.memory_types.EPISODIC)
    semantic = store.list(compactor.memory_types.SEMANTIC)
    assert len(episodic) == 1
    assert len(semantic) == 1
