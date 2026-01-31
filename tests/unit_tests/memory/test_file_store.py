import time

from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.models.raw_trace_item import RawTraceItem
from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.store.file_store import FileMemoryStore


def test_file_store_add_and_list_raw_trace(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    item = RawTraceItem(
        id="rt_001",
        ts=time.time(),
        turn_id="turn_0001",
        seq=1,
        trace_type="user",
        content="Hello",
        source_event="LLMUserMessageReadyEvent",
    )

    store.add([item])

    raw_items = store.list(MemoryType.RAW_TRACE)
    assert len(raw_items) == 1
    assert isinstance(raw_items[0], RawTraceItem)
    assert raw_items[0].id == "rt_001"
    assert raw_items[0].turn_id == "turn_0001"


def test_file_store_add_and_list_episodic(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    item = EpisodicItem(
        id="ep_0001",
        ts=time.time(),
        turn_ids=["turn_0001", "turn_0002"],
        summary="We discussed refactoring.",
        tags=["project"],
        salience=0.7,
    )

    store.add([item])

    episodic_items = store.list(MemoryType.EPISODIC)
    assert len(episodic_items) == 1
    assert isinstance(episodic_items[0], EpisodicItem)
    assert episodic_items[0].summary == "We discussed refactoring."


def test_file_store_add_and_list_semantic(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    item = SemanticItem(
        id="sem_0001",
        ts=time.time(),
        fact="Use python -m pytest.",
        tags=["preference"],
        confidence=0.9,
        salience=0.8,
    )

    store.add([item])

    semantic_items = store.list(MemoryType.SEMANTIC)
    assert len(semantic_items) == 1
    assert isinstance(semantic_items[0], SemanticItem)
    assert semantic_items[0].fact == "Use python -m pytest."


def test_file_store_list_limit(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    for i in range(3):
        item = RawTraceItem(
            id=f"rt_{i}",
            ts=time.time(),
            turn_id="turn_0001",
            seq=i + 1,
            trace_type="user",
            content=f"msg {i}",
            source_event="LLMUserMessageReadyEvent",
        )
        store.add([item])

    raw_items = store.list(MemoryType.RAW_TRACE, limit=2)
    assert len(raw_items) == 2
