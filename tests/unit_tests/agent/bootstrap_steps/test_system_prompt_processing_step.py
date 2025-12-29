# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_system_prompt_processing_step.py
import pytest
import logging
from unittest.mock import MagicMock, call, AsyncMock

from autobyteus.agent.bootstrap_steps.system_prompt_processing_step import SystemPromptProcessingStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.agent.context import AgentContext
from autobyteus.agent.status.manager import AgentStatusManager
from autobyteus.agent.system_prompt_processor import BaseSystemPromptProcessor

@pytest.fixture
def prompt_proc_step():
    """Provides a clean instance of the SystemPromptProcessingStep."""
    return SystemPromptProcessingStep()

@pytest.mark.asyncio
async def test_system_prompt_processing_success_with_processors(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_status_manager: AgentStatusManager,
    caplog
):
    """Tests successful prompt processing with a sequence of processors."""
    original_prompt = "Initial prompt."
    agent_context.config.system_prompt = original_prompt

    # Create mock processor instances
    mock_processor_1 = MagicMock(spec=BaseSystemPromptProcessor)
    mock_processor_1.get_name.return_value = "Processor1"
    mock_processor_1.get_order.return_value = 100
    mock_processor_1.process = MagicMock(return_value="Processed by P1.")
    
    mock_processor_2 = MagicMock(spec=BaseSystemPromptProcessor)
    mock_processor_2.get_name.return_value = "Processor2"
    mock_processor_2.get_order.return_value = 200
    mock_processor_2.process = MagicMock(return_value="Final processed by P2.")
    
    # Set the instances on the config
    agent_context.config.system_prompt_processors = [mock_processor_1, mock_processor_2]

    # Ensure the mock LLM instance has the method we're going to call
    agent_context.llm_instance.configure_system_prompt = MagicMock()

    with caplog.at_level(logging.INFO):
        success = await prompt_proc_step.execute(agent_context, mock_status_manager)

    assert success is True
    # The step no longer directly manages phase transitions. This is handled by the bootstrapper.
    # Therefore, no calls to the phase manager are expected from this step.
    assert f"Agent '{agent_context.agent_id}': Executing SystemPromptProcessingStep." in caplog.text
    assert "System prompt processor 'Processor1' applied successfully." in caplog.text
    assert "System prompt processor 'Processor2' applied successfully." in caplog.text
    
    # Verify the final prompt was stored in state AND set on the LLM instance
    final_prompt = "Final processed by P2."
    assert agent_context.state.processed_system_prompt == final_prompt
    agent_context.llm_instance.configure_system_prompt.assert_called_once_with(final_prompt)
    
    # Verify processors were called correctly
    mock_processor_1.process.assert_called_once_with(
        system_prompt=original_prompt,
        tool_instances=agent_context.tool_instances,
        agent_id=agent_context.agent_id,
        context=agent_context
    )
    mock_processor_2.process.assert_called_once_with(
        system_prompt="Processed by P1.",
        tool_instances=agent_context.tool_instances,
        agent_id=agent_context.agent_id,
        context=agent_context
    )
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_system_prompt_processing_success_no_processors(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_status_manager: AgentStatusManager,
    caplog
):
    """Tests successful execution when no processors are configured."""
    original_prompt = "Prompt without processors."
    agent_context.config.system_prompt = original_prompt
    agent_context.config.system_prompt_processors = [] 
    
    agent_context.llm_instance.configure_system_prompt = MagicMock()

    with caplog.at_level(logging.DEBUG):
        success = await prompt_proc_step.execute(agent_context, mock_status_manager)

    assert success is True
    # The step no longer directly manages phase transitions.
    assert "No system prompt processors configured. Using system prompt as is." in caplog.text
    
    # Verify the original prompt was stored and set
    assert agent_context.state.processed_system_prompt == original_prompt
    agent_context.llm_instance.configure_system_prompt.assert_called_once_with(original_prompt)
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_execute_fails_if_no_llm_instance(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_status_manager: AgentStatusManager,
    caplog
):
    """Tests that the step fails if the LLM instance isn't in the context."""
    agent_context.state.llm_instance = None # Critical setup for this test
    agent_context.config.llm_instance = None

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_status_manager)
    
    assert success is False
    assert "Critical failure during system prompt processing step: LLM instance not found" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert "LLM instance not found" in enqueued_event.error_message

@pytest.mark.asyncio
async def test_system_prompt_processing_failure_processor_error(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_status_manager: AgentStatusManager,
    caplog
):
    """Tests failure when a processor instance raises an exception."""
    agent_context.config.system_prompt = "Prompt that will fail."
    exception_message = "Processor internal error"
    
    failing_processor = MagicMock(spec=BaseSystemPromptProcessor)
    failing_processor.get_name.return_value = "FailingProcessor"
    failing_processor.process.side_effect = ValueError(exception_message)
    
    agent_context.config.system_prompt_processors = [failing_processor]

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_status_manager)

    assert success is False
    # The step no longer directly manages phase transitions.
    
    expected_error_log = f"Agent '{agent_context.agent_id}': Error applying system prompt processor 'FailingProcessor': {exception_message}"
    assert expected_error_log in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert enqueued_event.error_message == expected_error_log

@pytest.mark.asyncio
async def test_system_prompt_processing_invalid_processor_type(
    prompt_proc_step: SystemPromptProcessingStep,
    agent_context: AgentContext,
    mock_status_manager: AgentStatusManager,
    caplog
):
    """Tests failure when an item in the processor list is not a valid type."""
    agent_context.config.system_prompt_processors = ["not_a_processor_instance"]

    with caplog.at_level(logging.ERROR):
        success = await prompt_proc_step.execute(agent_context, mock_status_manager)

    assert success is False
    assert "Invalid system prompt processor configuration type" in caplog.text
    # In this specific case, an AgentErrorEvent *is* enqueued by the general exception handler
    # in the execute method, so this assertion needs to be updated.
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert "Invalid system prompt processor configuration type" in enqueued_event.error_message
