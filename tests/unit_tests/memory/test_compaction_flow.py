import time

from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


class FakeSummarizer(Summarizer):
    def summarize(self, traces):
        return CompactionResult(
            episodic_summary="Summary",
            semantic_facts=[
                {"fact": "Fact A", "tags": ["decision"], "confidence": 0.9},
                {"fact": "Fact B", "tags": [], "confidence": 0.5},
            ],
        )


def test_compactor_compact_stores_items(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=FakeSummarizer())

    trace_1 = RawTraceItem(
        id="rt_1",
        ts=time.time(),
        turn_id="turn_0001",
        seq=1,
        trace_type="user",
        content="hi",
        source_event="LLMUserMessageReadyEvent",
    )
    trace_2 = RawTraceItem(
        id="rt_2",
        ts=time.time(),
        turn_id="turn_0002",
        seq=1,
        trace_type="user",
        content="later",
        source_event="LLMUserMessageReadyEvent",
    )
    store.add([trace_1, trace_2])

    result = compactor.compact(["turn_0001"])
    assert result is not None

    episodic_items = store.list(compactor.memory_types.EPISODIC)
    semantic_items = store.list(compactor.memory_types.SEMANTIC)

    assert len(episodic_items) == 1
    assert episodic_items[0].summary == "Summary"

    assert len(semantic_items) == 2
    assert all(isinstance(item, SemanticItem) for item in semantic_items)
    assert semantic_items[0].fact == "Fact A"

    remaining_raw = store.list_raw_trace_dicts()
    assert len(remaining_raw) == 1
    assert remaining_raw[0]["turn_id"] == "turn_0002"


def test_compactor_compact_no_turns_returns_none(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=FakeSummarizer())

    result = compactor.compact([])
    assert result is None
