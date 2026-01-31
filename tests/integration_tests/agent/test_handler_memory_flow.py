import os
import pytest
from types import SimpleNamespace

from openai import APIConnectionError

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.handlers.llm_user_message_ready_event_handler import LLMUserMessageReadyEventHandler
from autobyteus.agent.input_processor.memory_ingest_input_processor import MemoryIngestInputProcessor
from autobyteus.agent.events.agent_events import LLMUserMessageReadyEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.message.multimodal_message_builder import build_llm_user_message
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.memory.memory_manager import MemoryManager
from autobyteus.memory.store.file_store import FileMemoryStore
from autobyteus.memory.models.memory_types import MemoryType


class DummyWorkspace(BaseAgentWorkspace):
    def get_base_path(self) -> str:
        return "."


class DummyQueues:
    def __init__(self):
        self.internal_events = []
        self.tool_events = []

    async def enqueue_internal_system_event(self, event):
        self.internal_events.append(event)

    async def enqueue_tool_invocation_request(self, event):
        self.tool_events.append(event)

    async def enqueue_user_message(self, event):
        self.internal_events.append(event)


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
async def test_handler_memory_flow_with_lmstudio(tmp_path, lmstudio_llm):
    memory_manager = MemoryManager(store=FileMemoryStore(base_dir=tmp_path, agent_id="agent_handler_flow"))
    runtime_state = AgentRuntimeState(agent_id="agent_handler_flow", workspace=DummyWorkspace())
    runtime_state.memory_manager = memory_manager
    runtime_state.input_event_queues = DummyQueues()
    runtime_state.llm_instance = lmstudio_llm

    config = AgentConfig(
        name="HandlerAgent",
        role="tester",
        description="Handler memory integration",
        llm_instance=lmstudio_llm,
        system_prompt=None,
        tools=[],
        input_processors=[MemoryIngestInputProcessor()],
    )

    context = AgentContext(agent_id=runtime_state.agent_id, config=config, state=runtime_state)
    context.state.status_manager_ref = SimpleNamespace(
        notifier=SimpleNamespace(
            notify_agent_segment_event=lambda *_args, **_kwargs: None,
            notify_agent_error_output_generation=lambda *_args, **_kwargs: None,
        )
    )

    # Simulate input processor stage
    agent_input = AgentInputUserMessage(content="Please respond with the word 'pong'.")
    await MemoryIngestInputProcessor().process(agent_input, context, triggering_event=None)  # type: ignore[arg-type]

    llm_user_message = build_llm_user_message(agent_input)
    event = LLMUserMessageReadyEvent(llm_user_message=llm_user_message)

    handler = LLMUserMessageReadyEventHandler()

    try:
        await handler.handle(event, context)
    except APIConnectionError:
        pytest.skip("Could not connect to LM Studio server.")
    finally:
        await lmstudio_llm.cleanup()

    raw_items = memory_manager.store.list(MemoryType.RAW_TRACE)
    assert len(raw_items) >= 2
    trace_types = {item.trace_type for item in raw_items}
    assert "user" in trace_types
    assert "assistant" in trace_types
    assert context.state.input_event_queues.internal_events
