from abc import ABC, abstractmethod
from typing import List

from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.compaction.compaction_result import CompactionResult


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, traces: List[RawTraceItem]) -> CompactionResult:
        raise NotImplementedError
