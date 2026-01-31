import os
import pytest

from openai import APIConnectionError

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.agent.llm_request_assembler import LLMRequestAssembler
from autobyteus.memory.compaction.compactor import Compactor
from autobyteus.memory.compaction.compaction_result import CompactionResult
from autobyteus.memory.compaction.summarizer import Summarizer
from autobyteus.memory.policies.compaction_policy import CompactionPolicy


class DummySummarizer(Summarizer):
    def summarize(self, traces):
        summary = " ".join(t.content for t in traces if t.content)
        return CompactionResult(
            episodic_summary=summary or "summary",
            semantic_facts=[{"fact": "user wants pong", "confidence": 0.5}],
        )


@pytest.fixture
def lmstudio_llm():
    manual_model_id = os.getenv("LMSTUDIO_MODEL_ID")
    if manual_model_id:
        return LLMFactory.create_llm(model_identifier=manual_model_id)

    LLMFactory.reinitialize()
    models = LLMFactory.list_models_by_runtime(LLMRuntime.LMSTUDIO)
    if not models:
        pytest.skip("No LM Studio models found.")

    target_text_model = "qwen/qwen3-30b-a3b-2507"
    text_model = next((m for m in models if target_text_model in m.model_identifier), None)
    if not text_model:
        text_model = next((m for m in models if "vl" not in m.model_identifier.lower()), models[0])

    return LLMFactory.create_llm(model_identifier=text_model.model_identifier)


@pytest.mark.asyncio
async def test_memory_compaction_flow(tmp_path, lmstudio_llm):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_mem_compact")
    policy = CompactionPolicy(raw_tail_turns=1, trigger_ratio=0.1)
    compactor = Compactor(store=store, policy=policy, summarizer=DummySummarizer())
    memory_manager = MemoryManager(store=store, compaction_policy=policy, compactor=compactor)

    # Seed two prior turns
    for idx in range(2):
        turn_id = memory_manager.start_turn()
        memory_manager.ingest_user_message(
            LLMUserMessage(content=f"turn {idx} user"),
            turn_id=turn_id,
            source_event="LLMUserMessageReadyEvent",
        )
        memory_manager.ingest_assistant_response(
            CompleteResponse(content=f"turn {idx} assistant"),
            turn_id=turn_id,
            source_event="LLMCompleteResponseReceivedEvent",
        )

    # Current turn
    current_turn_id = memory_manager.start_turn()
    user_message = LLMUserMessage(content="Please respond with the word 'pong'.")
    memory_manager.ingest_user_message(
        user_message,
        turn_id=current_turn_id,
        source_event="LLMUserMessageReadyEvent",
    )

    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=OpenAIChatRenderer(),
    )
    memory_manager.request_compaction()

    request = await assembler.prepare_request(
        processed_user_input=user_message,
        current_turn_id=current_turn_id,
        system_prompt=lmstudio_llm.config.system_message,
    )

    assert request.did_compact is True
    assert store.list(MemoryType.EPISODIC)
    assert store.list(MemoryType.SEMANTIC)

    try:
        response = await lmstudio_llm.send_messages(request.messages)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_llm.cleanup()

    assert response.content
    assert "pong" in response.content.lower()

    memory_manager.ingest_assistant_response(
        response,
        turn_id=current_turn_id,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    raw_items = store.list(MemoryType.RAW_TRACE)
    assert raw_items
    assert all(item.turn_id == current_turn_id for item in raw_items)
