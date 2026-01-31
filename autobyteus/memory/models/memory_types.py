from enum import Enum


class MemoryType(str, Enum):
    RAW_TRACE = "raw_trace"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
