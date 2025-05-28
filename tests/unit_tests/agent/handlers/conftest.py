import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.context.agent_context import AgentContext

from autobyteus.agent.events.agent_event_queues import AgentEventQueues, END_OF_STREAM_SENTINEL
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.status import AgentStatus
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.agent.context.agent_status_manager import AgentStatusManager
from autobyteus.events.event_emitter import EventEmitter
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig


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
    llm.add_system_message = MagicMock(wraps=llm.add_system_message)
    llm.add_user_message = MagicMock(wraps=llm.add_user_message)
    llm.add_assistant_message = MagicMock(wraps=llm.add_assistant_message)
    llm.latest_token_usage = MagicMock()

    return llm

@pytest.fixture
def mock_tool_instance():
    tool = MagicMock(spec=BaseTool)
    tool.execute = AsyncMock(return_value="Mocked tool result")
    tool.get_name = MagicMock(return_value="mock_tool")
    # Add mocks for tool_usage_xml and tool_usage_json if handlers rely on specific output
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
        definition.llm_response_processor_names = ["xml_tool_usage"] # Default, might change based on use_xml_format
        definition.system_prompt_processor_names = ["ToolDescriptionInjector", "ToolUsageExampleInjector"]
        definition.use_xml_tool_format = use_xml_format # Set the new flag
        
        if not use_xml_format: # If JSON, assume json_tool_usage processor
            definition.llm_response_processor_names = ["json_tool_usage"]
        return definition
    return _factory

@pytest.fixture
def mock_agent_definition_for_handlers(mock_agent_definition_for_handlers_factory):
    """Default mock AgentDefinition for handlers (uses XML format)."""
    return mock_agent_definition_for_handlers_factory(use_xml_format=True)


@pytest.fixture
def mock_workspace():
    workspace = MagicMock(spec=BaseAgentWorkspace)
    workspace.workspace_id = "test_workspace_id_handlers"
    return workspace

@pytest.fixture
def mock_event_queues_for_handlers():
    queues = MagicMock(spec=AgentEventQueues)
    for q_name in ["user_message_input_queue", "inter_agent_message_input_queue",
                   "tool_invocation_request_queue", "tool_result_input_queue",
                   "tool_execution_approval_queue", "internal_system_event_queue",
                   "assistant_output_chunk_queue", "assistant_final_message_queue",
                   "tool_interaction_log_queue"]:
        setattr(queues, q_name, AsyncMock(spec=asyncio.Queue))
        if "output" in q_name or "log" in q_name:
            getattr(queues, q_name).put = AsyncMock()
            getattr(queues, q_name).full = MagicMock(return_value=False)

    queues.enqueue_user_message = AsyncMock()
    queues.enqueue_inter_agent_message = AsyncMock()
    queues.enqueue_tool_invocation_request = AsyncMock()
    queues.enqueue_tool_result = AsyncMock()
    queues.enqueue_tool_approval_event = AsyncMock()
    queues.enqueue_internal_system_event = AsyncMock()
    queues.enqueue_end_of_stream_sentinel_to_output_queue = AsyncMock()
    
    queues._input_queues = [("mock_internal_q", queues.internal_system_event_queue)]
    queues.get_next_input_event = AsyncMock(return_value=None)
    queues.graceful_shutdown = AsyncMock()
    queues.END_OF_STREAM_SENTINEL = END_OF_STREAM_SENTINEL
    return queues

@pytest.fixture
def mock_agent_config(mock_agent_definition_for_handlers): # Uses the default XML-preferring definition
    agent_id = f"test_agent_cfg_{uuid.uuid4().hex[:6]}"
    # AgentConfig now correctly takes definition which carries use_xml_tool_format
    return AgentConfig(
        agent_id=agent_id,
        definition=mock_agent_definition_for_handlers,
        auto_execute_tools=True,
        llm_model_name="mock-model-name",
        custom_llm_config=None,
        custom_tool_config=None
    )

@pytest.fixture
def mock_agent_runtime_state(mock_agent_config, mock_event_queues_for_handlers, mock_workspace):
    return AgentRuntimeState(
        agent_id=mock_agent_config.agent_id,
        queues=mock_event_queues_for_handlers,
        workspace=mock_workspace,
        conversation_history=[],
        custom_data={}
    )

@pytest.fixture
def agent_context(mock_agent_config, mock_agent_runtime_state, mock_llm_instance_fixture, mock_tool_instance):
    # mock_agent_config uses mock_agent_definition_for_handlers, which defaults to use_xml_tool_format=True
    composite_context = AgentContext(config=mock_agent_config, state=mock_agent_runtime_state)
    
    composite_context.state.tool_instances = {mock_tool_instance.get_name(): mock_tool_instance}
    composite_context.state.status = AgentStatus.IDLE
    composite_context.state.llm_instance = mock_llm_instance_fixture

    composite_context.add_message_to_history = MagicMock(wraps=composite_context.add_message_to_history)
    composite_context.store_pending_tool_invocation = MagicMock(wraps=composite_context.store_pending_tool_invocation)
    composite_context.retrieve_pending_tool_invocation = MagicMock(wraps=composite_context.retrieve_pending_tool_invocation, return_value=None)
    composite_context.get_tool = MagicMock(wraps=composite_context.get_tool) 

    mock_status_manager_instance = MagicMock(spec=AgentStatusManager)
    # mock_status_manager_instance.emitter = MagicMock(spec=EventEmitter) # Emitter is now the manager itself
    # mock_status_manager_instance.emitter.emit = AsyncMock()
    mock_status_manager_instance.emit = AsyncMock() # Mock the emit method on the manager itself
    composite_context.state.status_manager_ref = mock_status_manager_instance
    
    return composite_context

@pytest.fixture
def mock_tool_invocation():
    invocation = MagicMock(spec=ToolInvocation)
    invocation.id = "test_tool_invocation_id_handlers"
    invocation.name = "mock_tool"
    invocation.arguments = {"arg1": "value1"}
    return invocation

