import pytest
import logging
from unittest.mock import MagicMock, AsyncMock

from autobyteus.agent.handlers.tool_invocation_execution_event_handler import (
    ToolInvocationExecutionEventHandler,
)
from autobyteus.agent.events.agent_events import ExecuteToolInvocationEvent, ToolResultEvent, GenericEvent
from autobyteus.agent.tool_invocation import ToolInvocation
from autobyteus.tools.base_tool import BaseTool


@pytest.fixture
def execution_handler():
    return ToolInvocationExecutionEventHandler()


@pytest.mark.asyncio
async def test_handle_execute_tool_success(execution_handler: ToolInvocationExecutionEventHandler, agent_context, mock_tool_instance, caplog):
    tool_name = "mock_tool"
    tool_args = {"param1": "value1"}
    invocation_id = "exec-tool-id-123"

    event = ExecuteToolInvocationEvent(
        tool_invocation=ToolInvocation(name=tool_name, arguments=tool_args, id=invocation_id)
    )

    mock_tool_instance.execute = AsyncMock(return_value="Successful execution result")

    with caplog.at_level(logging.INFO):
        await execution_handler.handle(event, agent_context)

    agent_context.status_manager.notifier.notify_agent_tool_execution_started.assert_called_once()
    agent_context.status_manager.notifier.notify_agent_data_tool_log.assert_any_call(
        {
            "log_entry": "[TOOL_RESULT] Successful execution result",
            "tool_invocation_id": invocation_id,
            "tool_name": tool_name,
        }
    )

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert isinstance(enqueued_event, ToolResultEvent)
    assert enqueued_event.tool_name == tool_name
    assert enqueued_event.result == "Successful execution result"
    assert enqueued_event.error is None
    assert enqueued_event.tool_invocation_id == invocation_id

    mock_tool_instance.execute.assert_called_once_with(context=agent_context, **tool_args)


@pytest.mark.asyncio
async def test_handle_execute_tool_not_found(execution_handler: ToolInvocationExecutionEventHandler, agent_context, caplog):
    tool_name = "non_existent_tool"
    tool_args = {"param": "val"}
    invocation_id = "notfound-tool-id-456"

    event = ExecuteToolInvocationEvent(
        tool_invocation=ToolInvocation(name=tool_name, arguments=tool_args, id=invocation_id)
    )

    agent_context.get_tool = MagicMock(return_value=None)

    with caplog.at_level(logging.ERROR):
        await execution_handler.handle(event, agent_context)

    error_message = f"Tool '{tool_name}' not found or configured for agent '{agent_context.agent_id}'."
    assert error_message in caplog.text

    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once_with(
        error_source=f"ToolExecution.ToolNotFound.{tool_name}",
        error_message=error_message,
    )

    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.error == error_message


@pytest.mark.asyncio
async def test_handle_execute_tool_exception(execution_handler: ToolInvocationExecutionEventHandler, agent_context, caplog):
    tool_name = "failing_tool"
    tool_args = {}
    invocation_id = "fail-tool-id-789"

    event = ExecuteToolInvocationEvent(
        tool_invocation=ToolInvocation(name=tool_name, arguments=tool_args, id=invocation_id)
    )

    failing_tool = MagicMock(spec=BaseTool)
    failing_tool.execute = AsyncMock(side_effect=Exception("Simulated tool execution failure!"))
    agent_context.get_tool = MagicMock(return_value=failing_tool)

    with caplog.at_level(logging.ERROR):
        await execution_handler.handle(event, agent_context)

    assert f"Error executing tool '{tool_name}' (ID: {invocation_id}):" in caplog.text

    agent_context.status_manager.notifier.notify_agent_error_output_generation.assert_called_once()
    kwargs = agent_context.status_manager.notifier.notify_agent_error_output_generation.call_args[1]
    assert kwargs["error_source"] == f"ToolExecution.Exception.{tool_name}"

    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert enqueued_event.tool_invocation_id == invocation_id
    assert enqueued_event.error is not None


@pytest.mark.asyncio
async def test_handle_preprocessor_failure(execution_handler: ToolInvocationExecutionEventHandler, agent_context):
    tool_name = "mock_tool"
    invocation_id = "preproc-fail-id"
    event = ExecuteToolInvocationEvent(
        tool_invocation=ToolInvocation(name=tool_name, arguments={}, id=invocation_id)
    )

    class FailingPreprocessor:
        def get_name(self):
            return "failing_pre"

        def get_order(self):
            return 1

        async def process(self, tool_invocation, context):
            raise RuntimeError("preprocessor failed")

    agent_context.config.tool_invocation_preprocessors = [FailingPreprocessor()]

    await execution_handler.handle(event, agent_context)

    agent_context.input_event_queues.enqueue_tool_result.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_tool_result.call_args[0][0]
    assert "Error in tool invocation preprocessor" in enqueued_event.error


@pytest.mark.asyncio
async def test_handle_invalid_event_type(execution_handler: ToolInvocationExecutionEventHandler, agent_context, caplog):
    invalid_event = GenericEvent(payload={}, type_name="wrong_event")

    with caplog.at_level(logging.WARNING):
        await execution_handler.handle(invalid_event, agent_context)

    assert "ToolInvocationExecutionEventHandler received non-ExecuteToolInvocationEvent" in caplog.text
    agent_context.input_event_queues.enqueue_tool_result.assert_not_called()


def test_execution_handler_initialization(caplog):
    with caplog.at_level(logging.INFO):
        ToolInvocationExecutionEventHandler()
    assert "ToolInvocationExecutionEventHandler initialized." in caplog.text
