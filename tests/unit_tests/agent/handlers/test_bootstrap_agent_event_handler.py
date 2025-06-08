# file: autobyteus/tests/unit_tests/agent/handlers/test_bootstrap_agent_event_handler.py
import pytest
import logging
from unittest.mock import MagicMock, AsyncMock, call, create_autospec

from autobyteus.agent.handlers.bootstrap_agent_event_handler import BootstrapAgentEventHandler
from autobyteus.agent.events import BootstrapAgentEvent, AgentReadyEvent, GenericEvent, AgentErrorEvent 
from autobyteus.agent.bootstrap_steps import ( 
    BaseBootstrapStep,
    AgentRuntimeQueueInitializationStep,
    ToolInitializationStep,
    SystemPromptProcessingStep,
    LLMConfigFinalizationStep,
    LLMInstanceCreationStep
)
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager

from autobyteus.tools.registry import ToolRegistry
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry
from autobyteus.llm.llm_factory import LLMFactory

@pytest.fixture
def mock_all_bootstrap_steps_ordered(monkeypatch):
    """
    Mocks each bootstrap step class used by BootstrapAgentEventHandler using create_autospec.
    Returns a list of the mock instances in the order they appear in the handler.
    """
    mock_instances = []
    
    # Mock for AgentRuntimeQueueInitializationStep
    mock_q_init_instance = create_autospec(AgentRuntimeQueueInitializationStep, instance=True)
    mock_q_init_instance.execute = AsyncMock(return_value=True) # execute is async
    monkeypatch.setattr("autobyteus.agent.handlers.bootstrap_agent_event_handler.AgentRuntimeQueueInitializationStep", lambda: mock_q_init_instance)
    mock_instances.append(mock_q_init_instance)

    # Mock for ToolInitializationStep
    mock_tool_init_instance = create_autospec(ToolInitializationStep, instance=True)
    mock_tool_init_instance.execute = AsyncMock(return_value=True)
    monkeypatch.setattr("autobyteus.agent.handlers.bootstrap_agent_event_handler.ToolInitializationStep", lambda tool_registry: mock_tool_init_instance)
    mock_instances.append(mock_tool_init_instance)

    # Mock for SystemPromptProcessingStep
    mock_prompt_proc_instance = create_autospec(SystemPromptProcessingStep, instance=True)
    mock_prompt_proc_instance.execute = AsyncMock(return_value=True)
    monkeypatch.setattr("autobyteus.agent.handlers.bootstrap_agent_event_handler.SystemPromptProcessingStep", lambda system_prompt_processor_registry: mock_prompt_proc_instance)
    mock_instances.append(mock_prompt_proc_instance)

    # Mock for LLMConfigFinalizationStep
    mock_llm_config_instance = create_autospec(LLMConfigFinalizationStep, instance=True)
    mock_llm_config_instance.execute = AsyncMock(return_value=True)
    monkeypatch.setattr("autobyteus.agent.handlers.bootstrap_agent_event_handler.LLMConfigFinalizationStep", lambda: mock_llm_config_instance)
    mock_instances.append(mock_llm_config_instance)

    # Mock for LLMInstanceCreationStep
    mock_llm_create_instance = create_autospec(LLMInstanceCreationStep, instance=True)
    mock_llm_create_instance.execute = AsyncMock(return_value=True)
    monkeypatch.setattr("autobyteus.agent.handlers.bootstrap_agent_event_handler.LLMInstanceCreationStep", lambda llm_factory: mock_llm_create_instance)
    mock_instances.append(mock_llm_create_instance)
    
    return mock_instances


@pytest.fixture
def bootstrap_handler(
    mock_tool_registry: ToolRegistry,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry,
    mock_llm_factory: LLMFactory,
    mock_all_bootstrap_steps_ordered # Use the correctly ordered mocks
):
    handler = BootstrapAgentEventHandler(
        tool_registry=mock_tool_registry,
        system_prompt_processor_registry=mock_system_prompt_processor_registry,
        llm_factory=mock_llm_factory
    )
    # The handler dynamically creates its steps list. We don't override handler.bootstrap_steps here
    # as the monkeypatching in mock_all_bootstrap_steps_ordered ensures the handler gets these mocks.
    return handler


@pytest.mark.asyncio
async def test_bootstrap_all_steps_succeed(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext, 
    mock_phase_manager: AgentPhaseManager, 
    mock_all_bootstrap_steps_ordered, 
    caplog
):
    event = BootstrapAgentEvent()
    
    if not hasattr(agent_context.input_event_queues, 'enqueue_internal_system_event'):
        agent_context.input_event_queues.enqueue_internal_system_event = AsyncMock()


    with caplog.at_level(logging.INFO):
        await bootstrap_handler.handle(event, agent_context)

    assert f"Agent '{agent_context.agent_id}': Starting orchestrated bootstrap process" in caplog.text
    
    
    for step_mock_instance in mock_all_bootstrap_steps_ordered:
        step_mock_instance.execute.assert_called_once_with(agent_context, mock_phase_manager)

    assert f"Agent '{agent_context.agent_id}': All bootstrap steps completed successfully. Agent is ready. Enqueuing AgentReadyEvent." in caplog.text 
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentReadyEvent) 

@pytest.mark.asyncio
async def test_bootstrap_one_step_fails(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_all_bootstrap_steps_ordered, 
    caplog
):
    event = BootstrapAgentEvent()
    
    failing_step_index = 1 
    failing_mock_step_instance = mock_all_bootstrap_steps_ordered[failing_step_index]
    failing_mock_step_instance.execute.return_value = False
    
    # MODIFIED: Get class name directly from the mock, which create_autospec sets up correctly.
    logged_failing_step_name = failing_mock_step_instance.__class__.__name__


    with caplog.at_level(logging.ERROR):
        await bootstrap_handler.handle(event, agent_context)

    
    for i in range(failing_step_index + 1):
        mock_all_bootstrap_steps_ordered[i].execute.assert_called_once_with(agent_context, mock_phase_manager)
    
    
    for i in range(failing_step_index + 1, len(mock_all_bootstrap_steps_ordered)):
        mock_all_bootstrap_steps_ordered[i].execute.assert_not_called()


    expected_log_message = f"Agent '{agent_context.agent_id}': Bootstrap step {logged_failing_step_name} failed. Halting bootstrap process."
    assert expected_log_message in caplog.text, \
        f"Expected log message not found. Logged name was '{logged_failing_step_name}'. Full caplog: {caplog.text}"
    
    
    if hasattr(agent_context.input_event_queues, 'enqueue_internal_system_event'):
        internal_event_calls = agent_context.input_event_queues.enqueue_internal_system_event.call_args_list
        assert not any(isinstance(call_args[0][0], AgentReadyEvent) for call_args in internal_event_calls)
    else: 
        pass 


@pytest.mark.asyncio
async def test_bootstrap_queue_initialization_step_fails(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_all_bootstrap_steps_ordered,
    caplog
):
    event = BootstrapAgentEvent()
    
    
    failing_step_mock = mock_all_bootstrap_steps_ordered[0]
    failing_step_mock.execute.return_value = False
    # MODIFIED: Get class name directly from the mock.
    logged_failing_step_name = failing_step_mock.__class__.__name__

    with caplog.at_level(logging.ERROR): 
        await bootstrap_handler.handle(event, agent_context)

    failing_step_mock.execute.assert_called_once_with(agent_context, mock_phase_manager)
    
    
    for i in range(1, len(mock_all_bootstrap_steps_ordered)):
        mock_all_bootstrap_steps_ordered[i].execute.assert_not_called()

    expected_log_message = f"Agent '{agent_context.agent_id}': Bootstrap step {logged_failing_step_name} failed. Halting bootstrap process."
    assert expected_log_message in caplog.text
    
    
    mock_phase_manager.notify_error_occurred.assert_called_once_with(
        f"Critical bootstrap failure at {logged_failing_step_name}",
        f"Agent '{agent_context.agent_id}' failed during {logged_failing_step_name}. Check logs for details."
    )
    assert f"Agent '{agent_context.agent_id}': {logged_failing_step_name} failed, which is critical for error reporting. Manual phase notification triggered." in caplog.text

    
    if hasattr(agent_context.input_event_queues, 'enqueue_internal_system_event'): 
        agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


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
    if hasattr(agent_context.input_event_queues, 'enqueue_internal_system_event'):
        agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


@pytest.mark.asyncio
async def test_bootstrap_phase_manager_not_found(
    bootstrap_handler: BootstrapAgentEventHandler,
    agent_context: AgentContext,
    caplog,
    mock_all_bootstrap_steps_ordered 
):
    event = BootstrapAgentEvent()
    agent_context.state.phase_manager_ref = None 

    with caplog.at_level(logging.CRITICAL): 
        await bootstrap_handler.handle(event, agent_context)
    
    assert f"Agent '{agent_context.agent_id}': AgentPhaseManager not found in context.state. Bootstrap cannot proceed" in caplog.text
    if hasattr(agent_context.input_event_queues, 'enqueue_internal_system_event'):
        agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()
    
    for step_mock_instance in mock_all_bootstrap_steps_ordered: 
        step_mock_instance.execute.assert_not_called()
