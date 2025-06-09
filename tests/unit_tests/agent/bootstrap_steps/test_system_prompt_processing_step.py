# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_system_prompt_processing_step.py
import pytest
import logging
from unittest.mock import MagicMock, call

from autobyteus.agent.bootstrap_steps.system_prompt_processing_step import SystemPromptProcessingStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry, BaseSystemPromptProcessor
from autobyteus.agent.registry.agent_specification import AgentSpecification

@pytest.fixture
def mock_processor_instance_fixture(mock_system_prompt_processor_registry): # Renamed to avoid conflict if used directly in test
    # This fixture provides the mock instance that the registry's get_processor method will return.
    # The actual mock_processor_instance used in tests will be this return value.
    return mock_system_prompt_processor_registry.get_processor.return_value

@pytest.fixture
def prompt_proc_step(mock_system_prompt_processor_registry: SystemPromptProcessorRegistry):
    return SystemPromptProcessingStep(system_prompt_processor_registry=mock_system_prompt_processor_registry)

@pytest.mark.asyncio
async def test_system_prompt_processing_success_with_processors(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry,
    mock_processor_instance_fixture: BaseSystemPromptProcessor, 
    caplog
):
    original_prompt = "Initial prompt. {{placeholder}}"
    agent_context.specification.system_prompt = original_prompt
    agent_context.specification.system_prompt_processor_names = ["Processor1", "Processor2"]
    
    processed_by_p1 = "Processed by P1. {{placeholder}}"
    processed_by_p2 = "Final processed by P2."

    # mock_processor_instance_fixture is the single mock instance returned by registry.get_processor
    # We configure its side_effect for multiple calls
    mock_processor_instance_fixture.process.side_effect = [
        processed_by_p1,
        processed_by_p2
    ]
    
    # Ensure the registry's get_processor returns our controlled mock instance for each processor name
    mock_system_prompt_processor_registry.get_processor.side_effect = [
        mock_processor_instance_fixture, # For Processor1
        mock_processor_instance_fixture  # For Processor2
    ]

    with caplog.at_level(logging.INFO):
        success = await prompt_proc_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_phase_manager.notify_initializing_prompt.assert_called_once()
    assert f"Agent '{agent_context.agent_id}': Executing SystemPromptProcessingStep." in caplog.text
    assert f"System prompt processor 'Processor1' applied successfully." in caplog.text
    assert f"System prompt processor 'Processor2' applied successfully." in caplog.text
    assert agent_context.state.processed_system_prompt == processed_by_p2
    
    mock_processor_instance_fixture.process.assert_has_calls([
        call(
            system_prompt=original_prompt,
            tool_instances=agent_context.state.tool_instances,
            agent_id=agent_context.agent_id,
            context=agent_context
        ),
        call(
            system_prompt=processed_by_p1,
            tool_instances=agent_context.state.tool_instances,
            agent_id=agent_context.agent_id,
            context=agent_context
        )
    ])
    assert mock_processor_instance_fixture.process.call_count == 2
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_system_prompt_processing_success_no_processors(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog
):
    original_prompt = "Prompt without processors."
    agent_context.specification.system_prompt = original_prompt
    agent_context.specification.system_prompt_processor_names = [] 

    with caplog.at_level(logging.DEBUG):
        success = await prompt_proc_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_phase_manager.notify_initializing_prompt.assert_called_once()
    assert "No system prompt processors configured. Using system prompt as is." in caplog.text
    assert agent_context.state.processed_system_prompt == original_prompt
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_system_prompt_processing_failure_individual_processor_error(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry,
    mock_processor_instance_fixture: BaseSystemPromptProcessor,
    caplog
):
    agent_context.specification.system_prompt = "Prompt that will fail."
    processor_name_that_fails = "FailingProcessor"
    agent_context.specification.system_prompt_processor_names = [processor_name_that_fails]
    exception_message = "Processor internal error"
    
    mock_processor_instance_fixture.process.side_effect = ValueError(exception_message)
    mock_system_prompt_processor_registry.get_processor.return_value = mock_processor_instance_fixture

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_phase_manager)

    assert success is False
    mock_phase_manager.notify_initializing_prompt.assert_called_once()
    
    expected_error_log = f"Agent '{agent_context.agent_id}': Error applying system prompt processor '{processor_name_that_fails}': {exception_message}"
    assert expected_error_log in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert enqueued_event.error_message == expected_error_log
    assert enqueued_event.exception_details == str(ValueError(exception_message))

@pytest.mark.asyncio
async def test_system_prompt_processing_failure_processor_not_found(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry,
    caplog
):
    agent_context.specification.system_prompt = "Prompt with missing processor."
    processor_name_not_found = "MissingProcessor"
    agent_context.specification.system_prompt_processor_names = [processor_name_not_found]
    
    mock_system_prompt_processor_registry.get_processor.return_value = None # Simulate processor not found

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_phase_manager)

    assert success is False
    mock_phase_manager.notify_initializing_prompt.assert_called_once()
    
    expected_error_log = f"Agent '{agent_context.agent_id}': System prompt processor '{processor_name_not_found}' not found in registry. This is a configuration error."
    assert expected_error_log in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert enqueued_event.error_message == expected_error_log
    assert enqueued_event.exception_details is None

@pytest.mark.asyncio
async def test_system_prompt_processing_failure_step_setup_error(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_system_prompt_processor_registry: SystemPromptProcessorRegistry, # Keep this to allow prompt_proc_step init
    caplog
):
    # Simulate an error before the processor loop, e.g., accessing a misconfigured specification
    # For this, we can make agent_context.specification.system_prompt raise an error when accessed
    
    original_specification = agent_context.specification 
    faulty_specification_mock = MagicMock(spec=type(original_specification)) # Mock to replace specification
    faulty_specification_mock.system_prompt_processor_names = ["AnyProcessor"] # Needed to enter the loop part of try
    
    # Make accessing 'system_prompt' on this mock raise an error
    setup_error_message = "Faulty specification access"
    type(faulty_specification_mock).system_prompt = property(fget=MagicMock(side_effect=AttributeError(setup_error_message)))
    
    agent_context.specification = faulty_specification_mock # Temporarily replace specification on context

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_phase_manager)
    
    agent_context.specification = original_specification # Restore original specification

    assert success is False
    mock_phase_manager.notify_initializing_prompt.assert_called_once() 
    
    expected_error_log = f"Agent '{agent_context.agent_id}': Critical failure during system prompt processing step setup: {setup_error_message}"
    assert expected_error_log in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert enqueued_event.error_message == expected_error_log
    assert enqueued_event.exception_details == str(AttributeError(setup_error_message))
