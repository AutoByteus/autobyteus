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
from autobyteus.agent.streaming.handlers.api_tool_call_streaming_response_handler import ApiToolCallStreamingResponseHandler
from autobyteus.agent.events.agent_events import ToolResultEvent
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.usage.formatters.openai_json_schema_formatter import OpenAiJsonSchemaFormatter


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
async def test_memory_tool_call_flow(tmp_path, lmstudio_llm):
    store = FileMemoryStore(base_dir=tmp_path, agent_id="agent_tool_flow")
    memory_manager = MemoryManager(store=store)

    tool_def = default_tool_registry.get_tool_definition("write_file")
    assert tool_def is not None
    tool_schema = OpenAiJsonSchemaFormatter().provide(tool_def)

    turn_id = memory_manager.start_turn()
    user_message = LLMUserMessage(content="Please write a python script named 'hello_world.py' that prints 'Hello World'.")
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

    handler = ApiToolCallStreamingResponseHandler()

    try:
        async for chunk in lmstudio_llm.stream_messages(request.messages, tools=[tool_schema]):
            handler.feed(chunk)
        handler.finalize()
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")

    invocations = handler.get_all_invocations()
    if not invocations:
        pytest.skip("Model did not emit tool calls.")

    for invocation in invocations:
        invocation.turn_id = turn_id
        memory_manager.ingest_tool_intent(invocation, turn_id=turn_id)
        result_event = ToolResultEvent(
            tool_name=invocation.name,
            result="OK",
            tool_invocation_id=invocation.id,
            tool_args=invocation.arguments,
            turn_id=turn_id,
        )
        memory_manager.ingest_tool_result(result_event, turn_id=turn_id)

    followup_message = LLMUserMessage(content="All tools finished. Please respond with 'done'.")
    follow_request = await assembler.prepare_request(
        processed_user_input=followup_message,
        current_turn_id=turn_id,
        system_prompt=lmstudio_llm.config.system_message,
    )

    try:
        follow_response = await lmstudio_llm.send_messages(follow_request.messages)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_llm.cleanup()

    assert follow_response.content
    assert "done" in follow_response.content.lower()

    memory_manager.ingest_assistant_response(
        CompleteResponse(content=follow_response.content),
        turn_id=turn_id,
        source_event="LLMCompleteResponseReceivedEvent",
    )

    raw_items = store.list(MemoryType.RAW_TRACE)
    trace_types = {item.trace_type for item in raw_items}
    assert "tool_call" in trace_types
    assert "tool_result" in trace_types
    assert "assistant" in trace_types
