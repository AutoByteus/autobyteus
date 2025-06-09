# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_tool_initialization_step.py
import pytest
import logging
from unittest.mock import MagicMock, call

from autobyteus.agent.bootstrap_steps.tool_initialization_step import ToolInitializationStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.context import AgentContext # For type hinting
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager # For type hinting
from autobyteus.tools.registry import ToolRegistry # For type hinting

@pytest.fixture
def tool_init_step(mock_tool_registry: ToolRegistry):
    return ToolInitializationStep(tool_registry=mock_tool_registry)

@pytest.mark.asyncio
async def test_tool_initialization_success_with_tools(
    tool_init_step: ToolInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_tool_registry: ToolRegistry,
    mock_tool_instance: BaseTool,
    caplog
):
    agent_context.specification.tool_names = ["tool1", "tool2"]
    mock_tool_registry.create_tool.side_effect = [mock_tool_instance, mock_tool_instance]

    with caplog.at_level(logging.INFO):
        success = await tool_init_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_phase_manager.notify_initializing_tools.assert_called_once()
    assert f"Agent '{agent_context.agent_id}': Executing ToolInitializationStep." in caplog.text
    assert f"Agent '{agent_context.agent_id}': 2 tools instantiated and stored" in caplog.text
    assert len(agent_context.state.tool_instances) == 2
    assert "tool1" in agent_context.state.tool_instances
    assert "tool2" in agent_context.state.tool_instances
    mock_tool_registry.create_tool.assert_has_calls([
        call("tool1", None),
        call("tool2", None)
    ])
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_tool_initialization_success_no_tools(
    tool_init_step: ToolInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog
):
    agent_context.specification.tool_names = [] # No tools defined

    with caplog.at_level(logging.INFO):
        success = await tool_init_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_phase_manager.notify_initializing_tools.assert_called_once()
    assert "No tool names defined. Tool initialization skipped." in caplog.text
    assert agent_context.state.tool_instances == {}
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_tool_initialization_failure_tool_creation_error(
    tool_init_step: ToolInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_tool_registry: ToolRegistry,
    caplog
):
    agent_context.specification.tool_names = ["failing_tool"]
    exception_message = "Tool creation failed in registry"
    mock_tool_registry.create_tool.side_effect = ValueError(exception_message)

    with caplog.at_level(logging.ERROR):
        success = await tool_init_step.execute(agent_context, mock_phase_manager)

    assert success is False
    mock_phase_manager.notify_initializing_tools.assert_called_once()
    assert f"Critical failure during tool initialization: {exception_message}" in caplog.text
    
    # Ensure tool_instances is set to empty dict on failure if it was None
    if agent_context.state.tool_instances is None: # Check needed if initial state could be None
        assert agent_context.state.tool_instances == {}
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert exception_message in enqueued_event.error_message

@pytest.mark.asyncio
async def test_tool_initialization_with_custom_config(
    tool_init_step: ToolInitializationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_tool_registry: ToolRegistry,
    mock_tool_instance: BaseTool
):
    agent_context.specification.tool_names = ["tool_with_config"]
    mock_custom_tool_config = {"tool_with_config": MagicMock()}
    agent_context.config.custom_tool_config = mock_custom_tool_config
    mock_tool_registry.create_tool.return_value = mock_tool_instance

    success = await tool_init_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_tool_registry.create_tool.assert_called_once_with("tool_with_config", mock_custom_tool_config["tool_with_config"])
    assert "tool_with_config" in agent_context.state.tool_instances
