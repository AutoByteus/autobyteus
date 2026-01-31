import time

from autobyteus.memory.models.episodic_item import EpisodicItem
from autobyteus.memory.models.semantic_item import SemanticItem
from autobyteus.memory.retrieval.retriever import Retriever
from autobyteus.memory.store.file_store import FileMemoryStore


def test_retriever_returns_memory_bundle(tmp_path):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_1")
    retriever = Retriever(store=store)

    episodic = EpisodicItem(
        id="ep_1",
        ts=time.time(),
        turn_ids=["turn_0001"],
        summary="Did a thing.",
    )
    semantic = SemanticItem(
        id="sem_1",
        ts=time.time(),
        fact="Use python -m pytest.",
    )

    store.add([episodic, semantic])

    bundle = retriever.retrieve(max_episodic=1, max_semantic=1)
    assert len(bundle.episodic) == 1
    assert len(bundle.semantic) == 1
    assert bundle.episodic[0].summary == "Did a thing."
    assert bundle.semantic[0].fact == "Use python -m pytest."
