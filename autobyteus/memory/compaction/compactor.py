import time
from typing import List, Optional

from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.policies.compaction_policy import CompactionPolicy
from autobyteus.memory.store.base_store import MemoryStore


class Compactor:
    def __init__(self, store: MemoryStore, policy: CompactionPolicy, summarizer: Summarizer):
        self.store = store
        self.policy = policy
        self.summarizer = summarizer
        self.memory_types = MemoryType

    def select_compaction_window(self) -> List[str]:
        raw_items = self.store.list(MemoryType.RAW_TRACE)
        turn_ids: List[str] = []
        seen = set()
        for item in raw_items:
            if not isinstance(item, RawTraceItem):
                continue
            if item.turn_id not in seen:
                seen.add(item.turn_id)
                turn_ids.append(item.turn_id)

        if self.policy.raw_tail_turns <= 0:
            return turn_ids
        if len(turn_ids) <= self.policy.raw_tail_turns:
            return []
        return turn_ids[:-self.policy.raw_tail_turns]

    def get_traces_for_turns(self, turn_ids: List[str]) -> List[RawTraceItem]:
        raw_items = self.store.list(MemoryType.RAW_TRACE)
        turn_set = set(turn_ids)
        return [
            item
            for item in raw_items
            if isinstance(item, RawTraceItem) and item.turn_id in turn_set
        ]

    def compact(self, turn_ids: List[str]) -> Optional[CompactionResult]:
        if not turn_ids:
            return None

        traces = self.get_traces_for_turns(turn_ids)
        result = self.summarizer.summarize(traces)

        episodic_item = EpisodicItem(
            id=f"ep_{int(time.time() * 1000)}",
            ts=time.time(),
            turn_ids=turn_ids,
            summary=result.episodic_summary,
            tags=[],
            salience=0.0,
        )

        semantic_items = []
        for idx, fact_data in enumerate(result.semantic_facts, start=1):
            semantic_items.append(
                SemanticItem(
                    id=f"sem_{int(time.time() * 1000)}_{idx}",
                    ts=time.time(),
                    fact=fact_data.get("fact", ""),
                    tags=fact_data.get("tags", []),
                    confidence=fact_data.get("confidence", 0.0),
                    salience=0.0,
                )
            )

        self.store.add([episodic_item, *semantic_items])
        self._prune_raw_traces(turn_ids)
        return result

    def _prune_raw_traces(self, compacted_turn_ids: List[str]) -> None:
        raw_items = self.store.list(MemoryType.RAW_TRACE)
        remaining_turns = {
            item.turn_id
            for item in raw_items
            if isinstance(item, RawTraceItem) and item.turn_id not in compacted_turn_ids
        }
        prune = getattr(self.store, "prune_raw_traces", None)
        if callable(prune):
            prune(keep_turn_ids=remaining_turns, archive=True)
