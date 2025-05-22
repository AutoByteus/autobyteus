import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

import pytest

# Assuming these paths are correct relative to a common root for autobyteus and tests
# If tests are outside autobyteus main package, adjust sys.path or use proper packaging
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


@pytest.fixture
def mock_llm_instance():
    llm = MagicMock(spec=BaseLLM)
    llm.stream_user_message = AsyncMock(return_value=AsyncMock()) # Make it an async generator
    llm.cleanup = AsyncMock()
    return llm

@pytest.fixture
def mock_tool_instance():
    tool = MagicMock(spec=BaseTool)
    tool.execute = AsyncMock(return_value="Mocked tool result")
    tool.get_name = MagicMock(return_value="mock_tool")
    return tool

@pytest.fixture
def mock_agent_definition():
    definition = MagicMock(spec=AgentDefinition)
    definition.name = "test_agent_def"
    definition.role = "test_role"
    definition.description = "A test agent definition."
    definition.system_prompt = "Test system prompt."
    definition.tool_names = ["mock_tool"]
    definition.input_processor_names = []
    definition.llm_response_processor_names = ["xml_tool_usage"] # Default
    return definition

@pytest.fixture
def mock_workspace():
    workspace = MagicMock(spec=BaseAgentWorkspace)
    workspace.workspace_id = "test_workspace_id"
    return workspace

@pytest.fixture
def mock_event_queues():
    queues = MagicMock(spec=AgentEventQueues)
    queues.user_message_input_queue = AsyncMock(spec=asyncio.Queue)
    queues.inter_agent_message_input_queue = AsyncMock(spec=asyncio.Queue)
    queues.tool_invocation_request_queue = AsyncMock(spec=asyncio.Queue)
    queues.tool_result_input_queue = AsyncMock(spec=asyncio.Queue)
    queues.tool_execution_approval_queue = AsyncMock(spec=asyncio.Queue)
    queues.internal_system_event_queue = AsyncMock(spec=asyncio.Queue)
    
    queues.assistant_output_chunk_queue = AsyncMock(spec=asyncio.Queue)
    queues.assistant_final_message_queue = AsyncMock(spec=asyncio.Queue)
    queues.tool_interaction_log_queue = AsyncMock(spec=asyncio.Queue)

    # Mock enqueue methods
    queues.enqueue_user_message = AsyncMock()
    queues.enqueue_inter_agent_message = AsyncMock()
    queues.enqueue_tool_invocation_request = AsyncMock()
    queues.enqueue_tool_result = AsyncMock()
    queues.enqueue_tool_approval_event = AsyncMock()
    queues.enqueue_internal_system_event = AsyncMock()
    queues.enqueue_end_of_stream_sentinel_to_output_queue = AsyncMock()
    
    queues._input_queues = [
        ("user_message_input_queue", queues.user_message_input_queue),
        ("internal_system_event_queue", queues.internal_system_event_queue), # Add more as needed
    ]
    queues.get_next_input_event = AsyncMock(return_value=None) # Default to no event
    queues.graceful_shutdown = AsyncMock()

    # Add END_OF_STREAM_SENTINEL to queues instance for access
    queues.END_OF_STREAM_SENTINEL = END_OF_STREAM_SENTINEL
    return queues

@pytest.fixture
def mock_emitter():
    return MagicMock(spec=EventEmitter)

@pytest.fixture
def mock_agent_status_manager(mock_agent_context_for_status_manager, mock_emitter):
    # This fixture depends on a context that is being initialized
    # This is a bit tricky. Let's make agent_context depend on this, or provide a simplified context
    # For now, let's assume context is passed in.
    # The AgentStatusManager constructor sets context.status.
    # We need to mock context.status to be settable.
    status_manager = AgentStatusManager(context=mock_agent_context_for_status_manager, emitter=mock_emitter)
    return status_manager

@pytest.fixture
def mock_agent_context_for_status_manager(mock_agent_definition, mock_event_queues, mock_llm_instance, mock_tool_instance, mock_workspace):
    """A simplified context, primarily for AgentStatusManager tests if needed, or for AgentRuntime."""
    context = MagicMock(spec=AgentContext)
    context.agent_id = "test_agent_for_status_manager"
    context.definition = mock_agent_definition
    context.queues = mock_event_queues
    context.llm_instance = mock_llm_instance
    context.tool_instances = {"mock_tool": mock_tool_instance}
    context.workspace = mock_workspace
    context.auto_execute_tools = True
    context.status = None # AgentStatusManager will set this
    context.conversation_history = []
    context.pending_tool_approvals = {}
    context.custom_data = {}
    context.get_tool = MagicMock(side_effect=lambda name: context.tool_instances.get(name))
    context.add_message_to_history = MagicMock()
    context.store_pending_tool_invocation = MagicMock()
    context.retrieve_pending_tool_invocation = MagicMock(return_value=None)
    return context


@pytest.fixture
def agent_context(mock_agent_definition, mock_event_queues, mock_llm_instance, mock_tool_instance, mock_workspace):
    agent_id = f"test_agent_{uuid.uuid4().hex[:6]}"

    context = AgentContext(
        agent_id=agent_id,
        definition=mock_agent_definition,
        queues=mock_event_queues,
        llm_instance=mock_llm_instance,
        tool_instances={"mock_tool": mock_tool_instance},
        auto_execute_tools=True, 
        workspace=mock_workspace,
        conversation_history=[], # Initialized as list, can be appended by real method or mocked
        custom_data={}
    )
    context.status = AgentStatus.IDLE 
    
    mock_emitter_instance = MagicMock(spec=EventEmitter)
    mock_status_manager_instance = MagicMock(spec=AgentStatusManager)
    mock_status_manager_instance.emitter = mock_emitter_instance
    context.status_manager = mock_status_manager_instance

    # MODIFICATION: Explicitly mock methods on the real AgentContext instance
    # that we want to assert calls on.
    context.add_message_to_history = MagicMock(wraps=context.add_message_to_history)
    context.get_tool = MagicMock(wraps=context.get_tool)
    context.store_pending_tool_invocation = MagicMock(wraps=context.store_pending_tool_invocation)
    context.retrieve_pending_tool_invocation = MagicMock(wraps=context.retrieve_pending_tool_invocation)
    # Using `wraps` means the original method will still be called, but the MagicMock
    # wrapper will record the call, allowing assertions like assert_called_once_with.
    # If we don't want the original method to run (e.g., if it has side effects we don't want in a unit test),
    # then we would just assign `MagicMock()` without `wraps`.
    # For `add_message_to_history`, `store_pending_tool_invocation`, `retrieve_pending_tool_invocation`,
    # `wraps` is generally fine as their internal logic is simple and might be useful to keep.
    # For `get_tool`, `wraps` is also good as it will return the actual tool or None.

    return context

@pytest.fixture
def mock_tool_invocation():
    invocation = MagicMock(spec=ToolInvocation)
    invocation.id = "test_tool_invocation_id"
    invocation.name = "mock_tool"
    invocation.arguments = {"arg1": "value1"}
    return invocation

