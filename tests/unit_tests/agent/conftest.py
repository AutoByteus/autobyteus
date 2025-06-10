# file: autobyteus/tests/unit_tests/agent/conftest.py
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.context.agent_context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager 

from autobyteus.agent.events.agent_input_event_queue_manager import AgentInputEventQueueManager
from autobyteus.agent.events.notifiers import AgentExternalEventNotifier 

from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.context.phases import AgentOperationalPhase 
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.llm.utils.llm_config import LLMConfig

# This conftest provides common, simplified fixtures for agent-related unit tests.

@pytest.fixture
def mock_llm_instance():
    """Provides a mocked BaseLLM instance."""
    llm = MagicMock(spec=BaseLLM)
    llm.stream_user_message = MagicMock() # Should be an async generator mock if needed
    llm.config = LLMConfig(system_message="Initial system message.")
    llm.add_message_to_history = MagicMock()
    llm.cleanup = AsyncMock()
    return llm

@pytest.fixture
def mock_tool_instance():
    """Provides a mocked BaseTool instance."""
    tool = MagicMock(spec=BaseTool)
    tool.execute = AsyncMock(return_value="Mocked tool result")
    tool.get_name = MagicMock(return_value="mock_tool")
    tool.get_description = MagicMock(return_value="A mock tool for testing.")
    tool.get_argument_schema = MagicMock(return_value=None)
    tool.tool_usage_xml = MagicMock(return_value='<command name="mock_tool" />')
    tool.tool_usage_json = MagicMock(return_value={"name": "mock_tool"})
    return tool

@pytest.fixture
def mock_workspace():
    """Provides a mocked BaseAgentWorkspace."""
    workspace = MagicMock(spec=BaseAgentWorkspace)
    workspace.workspace_id = "test_workspace_id_handlers"
    return workspace

@pytest.fixture
def mock_input_event_queue_manager():
    """Provides a mocked AgentInputEventQueueManager."""
    manager = MagicMock(spec=AgentInputEventQueueManager)
    # Mocking individual queues and methods for fine-grained control in tests.
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
    
    manager.get_next_input_event = AsyncMock(return_value=None)
    manager.log_remaining_items_at_shutdown = MagicMock()
    return manager

@pytest.fixture
def mock_phase_manager():
    """Provides a mocked AgentPhaseManager."""
    notifier_mock = AsyncMock(spec=AgentExternalEventNotifier)
    # Mock all notify methods on the notifier to prevent actual event emissions
    for attr_name in dir(AgentExternalEventNotifier):
        if attr_name.startswith("notify_") and callable(getattr(AgentExternalEventNotifier, attr_name)):
            setattr(notifier_mock, attr_name, MagicMock())

    manager = MagicMock(spec=AgentPhaseManager)
    manager.notifier = notifier_mock 
    # Mock all notify methods on the phase manager itself
    for attr_name in dir(AgentPhaseManager):
        if attr_name.startswith("notify_") and callable(getattr(AgentPhaseManager, attr_name)):
            setattr(manager, attr_name, MagicMock())
            
    return manager

@pytest.fixture
def mock_agent_config(mock_llm_instance, mock_tool_instance):
    """
    Provides a default, valid AgentConfig using mocked components.
    Tests can override fields on this config as needed.
    """
    return AgentConfig(
        name="TestAgent",
        role="tester",
        description="An agent for testing.",
        llm_instance=mock_llm_instance,
        system_prompt="You are a test agent.",
        tools=[mock_tool_instance],
        auto_execute_tools=True
    )

@pytest.fixture
def mock_agent_runtime_state(mock_agent_config, mock_workspace):
    """Provides a default AgentRuntimeState."""
    state = AgentRuntimeState(
        agent_id=f"test_agent_{uuid.uuid4().hex[:6]}",
        workspace=mock_workspace
    )
    # Mock stateful methods directly on the state object if tests assert on them
    state.add_message_to_history = MagicMock()
    state.store_pending_tool_invocation = MagicMock()
    state.retrieve_pending_tool_invocation = MagicMock(return_value=None)
    return state

@pytest.fixture
def agent_context(mock_agent_config, mock_agent_runtime_state, mock_input_event_queue_manager, mock_phase_manager): 
    """
    Provides a fully-composed AgentContext ready for use in handler/step tests.
    It simulates a post-bootstrap state where essential components are already attached.
    """
    # Use the mock config to populate the state
    mock_agent_runtime_state.llm_instance = mock_agent_config.llm_instance
    mock_agent_runtime_state.tool_instances = {tool.get_name(): tool for tool in mock_agent_config.tools}

    composite_context = AgentContext(
        agent_id=mock_agent_runtime_state.agent_id,
        config=mock_agent_config, 
        state=mock_agent_runtime_state
    )
    
    # Simulate a post-bootstrap state for handlers:
    composite_context.state.input_event_queues = mock_input_event_queue_manager
    composite_context.state.current_phase = AgentOperationalPhase.IDLE 
    composite_context.state.phase_manager_ref = mock_phase_manager
    
    return composite_context

@pytest.fixture
def mock_tool_invocation():
    """Provides a mocked ToolInvocation."""
    invocation = MagicMock(spec=ToolInvocation)
    invocation.id = "test_tool_invocation_id"
    invocation.name = "mock_tool"
    invocation.arguments = {"arg1": "value1"}
    return invocation
