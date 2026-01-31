import os
import pytest
from types import SimpleNamespace

from openai import APIConnectionError

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.handlers.llm_user_message_ready_event_handler import LLMUserMessageReadyEventHandler
from autobyteus.agent.handlers.tool_invocation_request_event_handler import ToolInvocationRequestEventHandler
from autobyteus.agent.handlers.tool_result_event_handler import ToolResultEventHandler
from autobyteus.agent.input_processor.memory_ingest_input_processor import MemoryIngestInputProcessor
from autobyteus.agent.tool_execution_result_processor.memory_ingest_tool_result_processor import (
    MemoryIngestToolResultProcessor,
)
from autobyteus.agent.events.agent_events import LLMUserMessageReadyEvent, PendingToolInvocationEvent, ToolResultEvent, UserMessageReceivedEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.multimodal_message_builder import build_llm_user_message
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.models.memory_types import MemoryType
from autobyteus.tools.base_tool import BaseTool


class DummyWorkspace(BaseAgentWorkspace):
    def get_base_path(self) -> str:
        return "."


class DummyQueues:
    def __init__(self):
        self.internal_events = []
        self.tool_invocation_events = []
        self.tool_result_events = []
        self.user_message_events = []

    async def enqueue_internal_system_event(self, event):
        self.internal_events.append(event)

    async def enqueue_tool_invocation_request(self, event):
        self.tool_invocation_events.append(event)

    async def enqueue_tool_result(self, event):
        self.tool_result_events.append(event)

    async def enqueue_user_message(self, event):
        self.user_message_events.append(event)


class DummyTool(BaseTool):
    @classmethod
    def get_name(cls):
        return "write_file"

    @classmethod
    def get_description(cls):
        return "Dummy write file tool"

    @classmethod
    def get_argument_schema(cls):
        return None

    async def _execute(self, context, **kwargs):
        return "OK"


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
async def test_full_tool_roundtrip_flow(tmp_path, lmstudio_llm, monkeypatch):
    monkeypatch.setenv("AUTOBYTEUS_STREAM_PARSER", "api_tool_call")

    memory_manager = MemoryManager(store=FileMemoryStore(base_dir=tmp_path, agent_id="agent_full_tool"))
    runtime_state = AgentRuntimeState(agent_id="agent_full_tool", workspace=DummyWorkspace())
    runtime_state.memory_manager = memory_manager
    runtime_state.input_event_queues = DummyQueues()
    runtime_state.llm_instance = lmstudio_llm

    dummy_tool = DummyTool()
    config = AgentConfig(
        name="FullToolAgent",
        role="tester",
        description="Full tool roundtrip",
        llm_instance=lmstudio_llm,
        system_prompt=None,
        tools=[dummy_tool],
        input_processors=[MemoryIngestInputProcessor()],
        tool_execution_result_processors=[MemoryIngestToolResultProcessor()],
        auto_execute_tools=True,
    )
    runtime_state.tool_instances = {dummy_tool.get_name(): dummy_tool}

    context = AgentContext(agent_id=runtime_state.agent_id, config=config, state=runtime_state)
    context.state.status_manager_ref = SimpleNamespace(
        notifier=SimpleNamespace(
            notify_agent_segment_event=lambda *_args, **_kwargs: None,
            notify_agent_error_output_generation=lambda *_args, **_kwargs: None,
            notify_agent_data_tool_log=lambda *_args, **_kwargs: None,
            notify_agent_request_tool_invocation_approval=lambda *_args, **_kwargs: None,
            notify_agent_tool_invocation_auto_executing=lambda *_args, **_kwargs: None,
        )
    )

    # First user input
    agent_input = AgentInputUserMessage(content="Please write a python file named 'hello.py' that prints 'Hello'.")
    await MemoryIngestInputProcessor().process(agent_input, context, triggering_event=None)  # type: ignore[arg-type]
    llm_user_message = build_llm_user_message(agent_input)
    llm_event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message)

    handler = LLMUserMessageReadyEventHandler()
    try:
        await handler.handle(llm_event, context)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")

    if not runtime_state.input_event_queues.tool_invocation_events:
        pytest.skip("Model did not emit tool calls.")

    tool_invocation_handler = ToolInvocationRequestEventHandler()
    for event in list(runtime_state.input_event_queues.tool_invocation_events):
        assert isinstance(event, PendingToolInvocationEvent)
        await tool_invocation_handler.handle(event, context)

    assert runtime_state.input_event_queues.tool_result_events

    tool_result_handler = ToolResultEventHandler()
    for event in list(runtime_state.input_event_queues.tool_result_events):
        assert isinstance(event, ToolResultEvent)
        await tool_result_handler.handle(event, context)

    assert runtime_state.input_event_queues.user_message_events

    follow_event = runtime_state.input_event_queues.user_message_events[-1]
    assert isinstance(follow_event, UserMessageReceivedEvent)

    # Process follow-up message from tool results
    await MemoryIngestInputProcessor().process(follow_event.agent_input_user_message, context, triggering_event=None)  # type: ignore[arg-type]
    follow_llm_message = build_llm_user_message(follow_event.agent_input_user_message)
    follow_llm_event = LLMUserMessageReadyEvent(llm_user_message=follow_llm_message)

    try:
        await handler.handle(follow_llm_event, context)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_llm.cleanup()

    raw_items = memory_manager.store.list(MemoryType.RAW_TRACE)
    trace_types = {item.trace_type for item in raw_items}
    assert "tool_call" in trace_types
    assert "tool_result" in trace_types
    assert "assistant" in trace_types
