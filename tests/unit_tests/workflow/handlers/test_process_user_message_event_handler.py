# file: autobyteus/tests/unit_tests/workflow/handlers/test_process_user_message_event_handler.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.workflow.handlers.process_user_message_event_handler import ProcessUserMessageEventHandler
from autobyteus.workflow.events.workflow_events import ProcessUserMessageEvent
from autobyteus.workflow.context import WorkflowContext
from autobyteus.agent.agent import Agent
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage

@pytest.fixture
def handler():
    return ProcessUserMessageEventHandler()

@pytest.fixture
def event():
    return ProcessUserMessageEvent(
        user_message=AgentInputUserMessage(content="Hello workflow"),
        target_agent_name="Coordinator"
    )

@pytest.mark.asyncio
async def test_handle_success(handler: ProcessUserMessageEventHandler, event: ProcessUserMessageEvent, workflow_context: WorkflowContext, mock_agent: Agent):
    """
    Tests the happy path where TeamManager provides a ready agent.
    """
    workflow_context.team_manager.ensure_agent_is_ready = AsyncMock(return_value=mock_agent)

    await handler.handle(event, workflow_context)

    workflow_context.status_manager.notify_processing_started.assert_awaited_once()
    workflow_context.team_manager.ensure_agent_is_ready.assert_awaited_once_with("Coordinator")
    mock_agent.post_user_message.assert_awaited_once_with(event.user_message)
    workflow_context.status_manager.notify_processing_complete_and_idle.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_agent_not_found(handler: ProcessUserMessageEventHandler, event: ProcessUserMessageEvent, workflow_context: WorkflowContext):
    """
    Tests that an error is reported if the TeamManager returns None.
    """
    workflow_context.team_manager.ensure_agent_is_ready = AsyncMock(return_value=None)

    await handler.handle(event, workflow_context)

    workflow_context.status_manager.notify_error_occurred.assert_awaited_once()
    error_msg = workflow_context.status_manager.notify_error_occurred.call_args.args[0]
    assert "Agent 'Coordinator' not found or failed to start" in error_msg
    workflow_context.status_manager.notify_processing_complete_and_idle.assert_not_awaited()
