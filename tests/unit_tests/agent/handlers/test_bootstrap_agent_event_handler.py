# file: autobyteus/tests/unit_tests/agent/handlers/test_bootstrap_agent_event_handler.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, call

from autobyteus.agent.handlers.bootstrap_agent_event_handler import BootstrapAgentEventHandler
from autobyteus.agent.events import BootstrapAgentEvent, AgentStartedEvent, GenericEvent
from autobyteus.agent.bootstrap_steps.base_bootstrap_step import BaseBootstrapStep
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

# Mock dependencies for BootstrapAgentEventHandler
from autobyteus.tools.registry import ToolRegistry
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry
from autobyteus.llm.llm_factory import LLMFactory

@pytest.fixture
def mock_all_bootstrap_steps(monkeypatch):
    """
    Mocks the bootstrap step classes so that when BootstrapAgentEventHandler
    instantiates them, it receives pre-configured mock instances.
    Each mock instance will have an 'execute' AsyncMock method.
    Returns a list of these mock instances for assertion.
    """
    mock_tool_init_instance = AsyncMock(spec=BaseBootstrapStep)
    mock_tool_init_instance.execute = AsyncMock(return_value=True)
    # Keep the custom attribute for potential other uses or easier debugging, but primary assertion won't use it.
    mock_tool_init_instance.step_class_name_for_test = "ToolInitializationStep" 


    mock_prompt_proc_instance = AsyncMock(spec=BaseBootstrapStep)
    mock_prompt_proc_instance.execute = AsyncMock(return_value=True)
    mock_prompt_proc_instance.step_class_name_for_test = "SystemPromptProcessingStep"

    mock_llm_config_instance = AsyncMock(spec=BaseBootstrapStep)
    mock_llm_config_instance.execute = AsyncMock(return_value=True)
    mock_llm_config_instance.step_class_name_for_test = "LLMConfigFinalizationStep"

    mock_llm_create_instance = AsyncMock(spec=BaseBootstrapStep)
    mock_llm_create_instance.execute = AsyncMock(return_value=True)
    mock_llm_create_instance.step_class_name_for_test = "LLMInstanceCreationStep"
    
    step_mock_instances_to_return = [
        mock_tool_init_instance,
        mock_prompt_proc_instance,
        mock_llm_config_instance,
        mock_llm_create_instance
    ]
    
    monkeypatch.setattr(
        "autobyteus.agent.handlers.bootstrap_agent_event_handler.ToolInitializationStep", 
        lambda *, tool_registry: step_mock_instances_to_return[0] 
    )
    monkeypatch.setattr(
        "autobyteus.agent.handlers.bootstrap_agent_event_handler.SystemPromptProcessingStep", 
        lambda *, system_prompt_processor_registry: step_mock_instances_to_return[1] 
    )
    monkeypatch.setattr(
        "autobyteus.agent.handlers.bootstrap_agent_event_handler.LLMConfigFinalizationStep", 
        lambda: step_mock_instances_to_return[2] 
    )
    monkeypatch.setattr(
        "autobyteus.agent.handlers.bootstrap_agent_event_handler.LLMInstanceCreationStep", 
        lambda *, llm_factory: step_mock_instances_to_return[3] 
    )
    
    return step_mock_instances_to_return


@pytest.fixture
def bootstrap_handler(
    mock_tool_registry: ToolRegistry,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry,
    mock_llm_factory: LLMFactory,
    mock_all_bootstrap_steps 
):
    handler = BootstrapAgentEventHandler(
        tool_registry=mock_tool_registry,
        system_prompt_processor_registry=mock_system_prompt_processor_registry,
        llm_factory=mock_llm_factory
    )
    handler.bootstrap_steps = mock_all_bootstrap_steps 
    return handler


@pytest.mark.asyncio
async def test_bootstrap_all_steps_succeed(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager, 
    mock_all_bootstrap_steps, 
    caplog
):
    event = BootstrapAgentEvent()

    with caplog.at_level(logging.INFO):
        await bootstrap_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': Starting orchestrated bootstrap process" in caplog.text
    
    for step_mock_instance in mock_all_bootstrap_steps:
        step_mock_instance.execute.assert_called_once_with(agent_context, mock_phase_manager)

    assert f"Agent '{agent_context.agent_id}': All bootstrap steps completed successfully. Enqueuing AgentStartedEvent." in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentStartedEvent)

@pytest.mark.asyncio
async def test_bootstrap_one_step_fails(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_all_bootstrap_steps, 
    caplog
):
    event = BootstrapAgentEvent()
    
    failing_mock_step_instance = mock_all_bootstrap_steps[1] # e.g., SystemPromptProcessingStep mock
    failing_mock_step_instance.execute.return_value = False 
    
    # Determine the name that will actually be logged by the handler
    # The handler uses step_instance.__class__.__name__. For an AsyncMock(spec=BaseBootstrapStep),
    # this typically results in the spec's name if __class__ is properly influenced by spec,
    # or 'AsyncMock'. The traceback showed it was 'BaseBootstrapStep'.
    logged_failing_step_name = failing_mock_step_instance.__class__.__name__
    if logged_failing_step_name == 'AsyncMock' and failing_mock_step_instance.spec is not None: # More robust
        logged_failing_step_name = failing_mock_step_instance.spec.__name__


    with caplog.at_level(logging.ERROR):
        await bootstrap_handler.handle(event, agent_context)

    mock_all_bootstrap_steps[0].execute.assert_called_once_with(agent_context, mock_phase_manager)
    failing_mock_step_instance.execute.assert_called_once_with(agent_context, mock_phase_manager)
    
    mock_all_bootstrap_steps[2].execute.assert_not_called()
    mock_all_bootstrap_steps[3].execute.assert_not_called()

    # Assert based on the name the handler actually logs
    expected_log_message = f"Agent '{agent_context.agent_id}': Bootstrap step {logged_failing_step_name} failed. Halting bootstrap process."
    assert expected_log_message in caplog.text, \
        f"Expected log message not found. Logged name was '{logged_failing_step_name}'. Full caplog: {caplog.text}"
    
    internal_event_calls = agent_context.input_event_queues.enqueue_internal_system_event.call_args_list
    assert not any(isinstance(call_args[0][0], AgentStartedEvent) for call_args in internal_event_calls)


@pytest.mark.asyncio
async def test_bootstrap_handler_invalid_event(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    caplog
):
    invalid_event = GenericEvent(payload={}, type_name="some_other_event")
    
    with caplog.at_level(logging.WARNING):
        await bootstrap_handler.handle(invalid_event, agent_context) 
    
    assert "BootstrapAgentEventHandler received non-BootstrapAgentEvent" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_phase_manager_not_found(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    caplog
):
    event = BootstrapAgentEvent()
    agent_context.state.phase_manager_ref = None 

    with caplog.at_level(logging.CRITICAL): 
        await bootstrap_handler.handle(event, agent_context)
    
    assert f"Agent '{agent_context.agent_id}': AgentPhaseManager not found in context.state. Bootstrap cannot proceed" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()
    
    for step_mock_instance in bootstrap_handler.bootstrap_steps:
        step_mock_instance.execute.assert_not_called()

