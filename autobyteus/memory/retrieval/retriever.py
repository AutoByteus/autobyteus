from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.memory.retrieval.memory_bundle import MemoryBundle
from autobyteus.memory.store.base_store import MemoryStore


class Retriever:
    def __init__(self, store: MemoryStore):
        self.store = store

    def retrieve(self, max_episodic: int, max_semantic: int) -> MemoryBundle:
        episodic = self.store.list(MemoryType.EPISODIC, limit=max_episodic)
        semantic = self.store.list(MemoryType.SEMANTIC, limit=max_semantic)
        return MemoryBundle(episodic=episodic, semantic=semantic)
