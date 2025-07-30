# file: autobyteus/tests/unit_tests/workflow/test_agentic_workflow.py
import pytest
from unittest.mock import MagicMock, AsyncMock, create_autospec

from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.runtime.workflow_runtime import WorkflowRuntime
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@pytest.fixture
def mock_runtime():
    # The create_autospec function inspects the WorkflowRuntime class to create a mock
    # that has the same API. However, it often fails to discover instance attributes
    # that are defined within the __init__ method, such as 'context'.
    # The correct way to add these missing attributes to the spec'd mock is to
    # pass them as keyword arguments during creation.

    # 1. Create the nested mock object that we want to attach.
    mock_context = MagicMock()
    mock_context.config.coordinator_node.name = "Coordinator"
    mock_context.workflow_id = "mock-workflow-id"

    # 2. Create the autospec'd mock, passing the missing attributes as kwargs.
    # This ensures 'context' and 'is_running' are part of the mock's interface from the start.
    runtime = create_autospec(
        WorkflowRuntime,
        instance=True,
        context=mock_context,
        is_running=False
    )

    # 3. Reconfigure any methods that need specific mock types (e.g., AsyncMock).
    # create_autospec will have already created these as regular MagicMocks.
    runtime.start = MagicMock()
    runtime.submit_event = AsyncMock()

    return runtime

@pytest.fixture
def workflow(mock_runtime):
    return AgenticWorkflow(runtime=mock_runtime)

@pytest.mark.asyncio
async def test_post_message_starts_if_not_running(workflow: AgenticWorkflow, mock_runtime: MagicMock):
    """Tests that post_message calls start() if the runtime isn't running."""
    mock_runtime.is_running = False
    message = AgentInputUserMessage(content="test")
    
    await workflow.post_message(message)
    
    mock_runtime.start.assert_called_once()
    mock_runtime.submit_event.assert_awaited_once()

@pytest.mark.asyncio
async def test_post_message_no_target_defaults_to_coordinator(workflow: AgenticWorkflow, mock_runtime: MagicMock):
    """Tests that post_message defaults to the coordinator if no target is specified."""
    mock_runtime.is_running = True
    message = AgentInputUserMessage(content="test")

    await workflow.post_message(message, target_agent_name=None)

    mock_runtime.submit_event.assert_awaited_once()
    submitted_event = mock_runtime.submit_event.call_args.args[0]
    assert isinstance(submitted_event, ProcessUserMessageEvent)
    assert submitted_event.user_message is message
    assert submitted_event.target_agent_name == "Coordinator"

@pytest.mark.asyncio
async def test_post_message_with_target_uses_target(workflow: AgenticWorkflow, mock_runtime: MagicMock):
    """Tests that post_message uses the specified target agent name."""
    mock_runtime.is_running = True
    message = AgentInputUserMessage(content="test")
    target_name = "Specialist"

    await workflow.post_message(message, target_agent_name=target_name)

    mock_runtime.submit_event.assert_awaited_once()
    submitted_event = mock_runtime.submit_event.call_args.args[0]
    assert isinstance(submitted_event, ProcessUserMessageEvent)
    assert submitted_event.target_agent_name == target_name
