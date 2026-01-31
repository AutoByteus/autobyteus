import os
import pytest

from openai import APIConnectionError

from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.user_message import LLMUserMessage
from autobyteus.llm.prompt_renderers.openai_chat_renderer import OpenAIChatRenderer
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.agent.llm_request_assembler import LLMRequestAssembler


@pytest.fixture
def lmstudio_llm():
    manual_model_id = os.getenv("LMSTUDIO_MODEL_ID")
    if manual_model_id:
        llm = LLMFactory.create_llm(model_identifier=manual_model_id)
        return llm

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
async def test_memory_assembler_with_lmstudio(tmp_path, lmstudio_llm):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_mem_1")
    memory_manager = MemoryManager(store=store)

    turn_id = memory_manager.start_turn()
    user_message = LLMUserMessage(content="Please respond with the word 'pong'.")
    memory_manager.ingest_user_message(
        user_message,
        turn_id=turn_id,
        source_event="LLMUserMessageReadyEvent",
    )

    assembler = LLMRequestAssembler(
        memory_manager=memory_manager,
        renderer=OpenAIChatRenderer(),
    )

    request = await assembler.prepare_request(
        processed_user_input=user_message,
        current_turn_id=turn_id,
        system_prompt=lmstudio_llm.config.system_message,
    )

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
        turn_id=turn_id,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    raw_items = store.list(MemoryType.RAW_TRACE)
    assert len(raw_items) == 2
