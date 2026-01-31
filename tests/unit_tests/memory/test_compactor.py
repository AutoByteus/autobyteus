import time

from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.file_store import FileMemoryStore


def test_select_compaction_window_excludes_raw_tail(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=_NoopSummarizer())

    for turn_id in ["turn_0001", "turn_0002", "turn_0003"]:
        trace = RawTraceItem(
            id=f"rt_{turn_id}",
            ts=time.time(),
            turn_id=turn_id,
            seq=1,
            trace_type="user",
            content="hi",
            source_event="LLMUserMessageReadyEvent",
        )
        store.add([trace])

    window = compactor.select_compaction_window()
    assert window == ["turn_0001", "turn_0002"]


def test_get_traces_for_turns_filters_by_turn_id(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=_NoopSummarizer())

    trace1 = RawTraceItem(
        id="rt_1",
        ts=time.time(),
        turn_id="turn_0001",
        seq=1,
        trace_type="user",
        content="hi",
        source_event="LLMUserMessageReadyEvent",
    )
    trace2 = RawTraceItem(
        id="rt_2",
        ts=time.time(),
        turn_id="turn_0002",
        seq=1,
        trace_type="user",
        content="hello",
        source_event="LLMUserMessageReadyEvent",
    )
    store.add([trace1, trace2])

    traces = compactor.get_traces_for_turns(["turn_0002"])
    assert len(traces) == 1
    assert traces[0].turn_id == "turn_0002"


class _NoopSummarizer(Summarizer):
    def summarize(self, traces):
        return CompactionResult(episodic_summary="", semantic_facts=[])


class _FailSummarizer(Summarizer):
    def summarize(self, traces):
        raise RuntimeError("summarizer failed")


def test_compactor_does_not_prune_on_failure(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_fail")
    policy = CompactionPolicy(raw_tail_turns=1)
    compactor = Compactor(store=store, policy=policy, summarizer=_FailSummarizer())

    trace1 = RawTraceItem(
        id="rt_1",
        ts=time.time(),
        turn_id="turn_0001",
        seq=1,
        trace_type="user",
        content="hi",
        source_event="LLMUserMessageReadyEvent",
    )
    trace2 = RawTraceItem(
        id="rt_2",
        ts=time.time(),
        turn_id="turn_0002",
        seq=1,
        trace_type="user",
        content="hello",
        source_event="LLMUserMessageReadyEvent",
    )
    store.add([trace1, trace2])

    try:
        compactor.compact(["turn_0001"])
    except RuntimeError:
        pass

    remaining = store.list_raw_trace_dicts()
    assert {item["turn_id"] for item in remaining} == {"turn_0001", "turn_0002"}

    archive = store.read_archive_raw_traces()
    assert archive == []
