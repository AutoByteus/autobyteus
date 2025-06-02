import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager 

from autobyteus.agent.events.agent_input_event_queue_manager import AgentInputEventQueueManager
from autobyteus.agent.events.agent_output_data_manager import AgentOutputDataManager, END_OF_STREAM_SENTINEL

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.status import AgentStatus 
from autobyteus.agent.phases import AgentOperationalPhase 
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.events.event_emitter import EventEmitter 
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig

from autobyteus.tools.registry import ToolRegistry
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry
from autobyteus.llm.llm_factory import LLMFactory


@pytest.fixture
def mock_llm_instance_fixture():
    llm = MagicMock(spec=BaseLLM)
    llm._execute_before_hooks = AsyncMock()
    llm._execute_after_hooks = AsyncMock()
    llm._send_user_message_to_llm = AsyncMock()
    llm._stream_user_message_to_llm = MagicMock()
    llm.send_user_message = AsyncMock()
    llm.stream_user_message = MagicMock()
    llm.cleanup = AsyncMock()
    
    mock_model_obj = MagicMock(spec=LLMModel)
    mock_model_obj.name = "mock-model-name"
    mock_model_obj.value = "mock-model-value"
    mock_model_obj.provider = LLMProvider.OPENAI
    
    mock_llm_config = MagicMock(spec=LLMConfig)
    mock_llm_config.system_message = "Mock system message."
    mock_llm_config.pricing_config = TokenPricingConfig(input_token_pricing=0.0, output_token_pricing=0.0)
    mock_model_obj.default_config = mock_llm_config
    
    llm.model = mock_model_obj
    llm.config = mock_llm_config

    llm.messages = []
    llm.add_system_message = MagicMock() 
    llm.add_user_message = MagicMock()
    llm.add_assistant_message = MagicMock()
    llm.latest_token_usage = MagicMock()

    return llm

@pytest.fixture
def mock_tool_instance():
    tool = MagicMock(spec=BaseTool)
    tool.execute = AsyncMock(return_value="Mocked tool result")
    tool.get_name = MagicMock(return_value="mock_tool")
    tool.tool_usage_xml = MagicMock(return_value="<command name='mock_tool'></command>")
    tool.tool_usage_json = MagicMock(return_value={"name": "mock_tool", "description": "A mock tool.", "parameters": {}})
    return tool

@pytest.fixture
def mock_agent_definition_for_handlers_factory():
    """Factory to create mock AgentDefinition for handlers, allowing to set use_xml_tool_format."""
    def _factory(use_xml_format: bool = True):
        definition = MagicMock(spec=AgentDefinition)
        definition.name = "test_agent_def_handlers"
        definition.role = "test_role_handlers"
        definition.description = "A test agent definition for handlers."
        definition.system_prompt = "Test system prompt template for handlers. {{tools}} {{tool_examples}}"
        definition.tool_names = ["mock_tool"] 
        definition.input_processor_names = []
        definition.llm_response_processor_names = ["xml_tool_usage"]
        definition.system_prompt_processor_names = ["ToolDescriptionInjector", "ToolUsageExampleInjector"]
        definition.use_xml_tool_format = use_xml_format
        
        if not use_xml_format:
            definition.llm_response_processor_names = ["json_tool_usage"]
        return definition
    return _factory

@pytest.fixture
def mock_agent_definition_for_handlers(mock_agent_definition_for_handlers_factory):
    return mock_agent_definition_for_handlers_factory(use_xml_format=True)


@pytest.fixture
def mock_workspace():
    workspace = MagicMock(spec=BaseAgentWorkspace)
    workspace.workspace_id = "test_workspace_id_handlers"
    return workspace

@pytest.fixture
def mock_input_event_queue_manager():
    manager = MagicMock(spec=AgentInputEventQueueManager)
    manager.user_message_input_queue = AsyncMock(spec=asyncio.Queue)
    manager.inter_agent_message_input_queue = AsyncMock(spec=asyncio.Queue)
    manager.tool_invocation_request_queue = AsyncMock(spec=asyncio.Queue)
    manager.tool_result_input_queue = AsyncMock(spec=asyncio.Queue)
    manager.tool_execution_approval_queue = AsyncMock(spec=asyncio.Queue)
    manager.internal_system_event_queue = AsyncMock(spec=asyncio.Queue)

    manager.enqueue_user_message = AsyncMock()
    manager.enqueue_inter_agent_message = AsyncMock()
    manager.enqueue_tool_invocation_request = AsyncMock()
    manager.enqueue_tool_result = AsyncMock()
    manager.enqueue_tool_approval_event = AsyncMock()
    manager.enqueue_internal_system_event = AsyncMock()
    
    manager._input_queues = [("mock_internal_q", manager.internal_system_event_queue)]
    manager.get_next_input_event = AsyncMock(return_value=None) 
    manager.log_remaining_items_at_shutdown = MagicMock()
    return manager

@pytest.fixture
def mock_output_data_manager():
    manager = MagicMock(spec=AgentOutputDataManager)
    manager.pending_tool_approval_queue = AsyncMock(spec=asyncio.Queue)
    manager.assistant_output_chunk_queue = AsyncMock(spec=asyncio.Queue)
    manager.assistant_final_message_queue = AsyncMock(spec=asyncio.Queue)
    manager.tool_interaction_log_queue = AsyncMock(spec=asyncio.Queue)
    
    for q_name in ["pending_tool_approval_queue", "assistant_output_chunk_queue", 
                   "assistant_final_message_queue", "tool_interaction_log_queue"]:
        getattr(manager, q_name).put = AsyncMock()
        getattr(manager, q_name).full = MagicMock(return_value=False)

    manager.enqueue_pending_tool_approval_data = AsyncMock()
    manager.enqueue_assistant_chunk = AsyncMock()
    manager.enqueue_assistant_final_message = AsyncMock()
    manager.enqueue_tool_interaction_log = AsyncMock()
    manager.enqueue_end_of_stream_sentinel_to_output_queue = AsyncMock()
    manager.graceful_shutdown = AsyncMock()
    manager.log_remaining_items_at_shutdown = MagicMock()
    manager.END_OF_STREAM_SENTINEL = END_OF_STREAM_SENTINEL
    return manager


@pytest.fixture
def mock_agent_config(mock_agent_definition_for_handlers):
    agent_id = f"test_agent_cfg_{uuid.uuid4().hex[:6]}"
    return AgentConfig(
        agent_id=agent_id,
        definition=mock_agent_definition_for_handlers,
        auto_execute_tools=True,
        llm_model_name="mock-model-name", 
        custom_llm_config=None,
        custom_tool_config=None
    )

@pytest.fixture
def mock_agent_runtime_state(mock_agent_config, mock_input_event_queue_manager, mock_output_data_manager, mock_workspace):
    return AgentRuntimeState(
        agent_id=mock_agent_config.agent_id,
        input_event_queues=mock_input_event_queue_manager, 
        output_data_queues=mock_output_data_manager,       
        workspace=mock_workspace,
        conversation_history=[],
        custom_data={}
    )

@pytest.fixture
def mock_phase_manager():
    manager = MagicMock(spec=AgentPhaseManager)
    manager.notify_initializing_tools = MagicMock()
    manager.notify_initializing_prompt = MagicMock()
    manager.notify_initializing_llm = MagicMock()
    manager.notify_initialization_complete = MagicMock()
    return manager

@pytest.fixture
def agent_context(mock_agent_config, mock_agent_runtime_state, mock_llm_instance_fixture, mock_tool_instance, mock_phase_manager): 
    composite_context = AgentContext(config=mock_agent_config, state=mock_agent_runtime_state)
    
    composite_context.state.tool_instances = {mock_tool_instance.get_name(): mock_tool_instance}
    composite_context.state.current_phase = AgentOperationalPhase.IDLE 
    composite_context.state.llm_instance = mock_llm_instance_fixture
    composite_context.state.processed_system_prompt = "Processed system prompt for testing."
    composite_context.state.final_llm_config_for_creation = LLMConfig(system_message="Final system message.")

    composite_context.add_message_to_history = MagicMock(wraps=composite_context.add_message_to_history)
    composite_context.store_pending_tool_invocation = MagicMock(wraps=composite_context.store_pending_tool_invocation)
    composite_context.retrieve_pending_tool_invocation = MagicMock(wraps=composite_context.retrieve_pending_tool_invocation, return_value=None)
    composite_context.get_tool = MagicMock(wraps=composite_context.get_tool) 

    composite_context.state.phase_manager_ref = mock_phase_manager
    
    return composite_context

@pytest.fixture
def mock_tool_invocation():
    invocation = MagicMock(spec=ToolInvocation)
    invocation.id = "test_tool_invocation_id_handlers"
    invocation.name = "mock_tool"
    invocation.arguments = {"arg1": "value1"}
    return invocation

@pytest.fixture
def mock_tool_registry():
    registry = MagicMock(spec=ToolRegistry)
    registry.create_tool = MagicMock(return_value=MagicMock(spec=BaseTool)) 
    return registry

@pytest.fixture
def mock_system_prompt_processor_registry():
    registry = MagicMock(spec=SystemPromptProcessorRegistry)
    mock_processor_instance = MagicMock() 
    mock_processor_instance.process = MagicMock(side_effect=lambda system_prompt, **kwargs: system_prompt) 
    registry.get_processor = MagicMock(return_value=mock_processor_instance)
    return registry

@pytest.fixture
def mock_llm_factory():
    factory = MagicMock(spec=LLMFactory)
    factory.create_llm = MagicMock(return_value=MagicMock(spec=BaseLLM)) 
    return factory
