# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_llm_instance_creation_step.py
import pytest
import logging
from unittest.mock import MagicMock

from autobyteus.agent.bootstrap_steps.llm_instance_creation_step import LLMInstanceCreationStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig

@pytest.fixture
def llm_creation_step(mock_llm_factory: LLMFactory):
    return LLMInstanceCreationStep(llm_factory=mock_llm_factory)

@pytest.mark.asyncio
async def test_llm_instance_creation_success(
    llm_creation_step: LLMInstanceCreationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_llm_factory: LLMFactory,
    mock_llm_instance_fixture: BaseLLM, # Use the existing fixture for a mock LLM
    caplog
):
    # agent_context.state.final_llm_config_for_creation is already set by conftest
    # agent_context.config.llm_model_name is also set by conftest
    mock_llm_factory.create_llm.return_value = mock_llm_instance_fixture

    with caplog.at_level(logging.INFO):
        success = await llm_creation_step.execute(agent_context, mock_phase_manager)

    assert success is True
    mock_phase_manager.notify_initializing_llm.assert_called_once()
    assert f"Agent '{agent_context.agent_id}': Executing LLMInstanceCreationStep." in caplog.text
    assert f"Agent '{agent_context.agent_id}': LLM instance ({mock_llm_instance_fixture.__class__.__name__}) created successfully." in caplog.text
    
    mock_llm_factory.create_llm.assert_called_once_with(
        model_identifier=agent_context.config.llm_model_name,
        llm_config=agent_context.state.final_llm_config_for_creation
    )
    assert agent_context.state.llm_instance == mock_llm_instance_fixture
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()

@pytest.mark.asyncio
async def test_llm_instance_creation_failure_no_final_config(
    llm_creation_step: LLMInstanceCreationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog
):
    agent_context.state.final_llm_config_for_creation = None # Simulate missing config

    with caplog.at_level(logging.ERROR):
        success = await llm_creation_step.execute(agent_context, mock_phase_manager)

    assert success is False
    mock_phase_manager.notify_initializing_llm.assert_called_once() # Phase is notified before check
    assert "Critical failure creating LLM instance: Final LLMConfig not found" in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert "Final LLMConfig not found" in enqueued_event.error_message

@pytest.mark.asyncio
async def test_llm_instance_creation_failure_factory_error(
    llm_creation_step: LLMInstanceCreationStep,
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    mock_llm_factory: LLMFactory,
    caplog
):
    exception_message = "LLM factory failed"
    mock_llm_factory.create_llm.side_effect = RuntimeError(exception_message)

    with caplog.at_level(logging.ERROR):
        success = await llm_creation_step.execute(agent_context, mock_phase_manager)

    assert success is False
    mock_phase_manager.notify_initializing_llm.assert_called_once()
    assert f"Critical failure creating LLM instance: {exception_message}" in caplog.text
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert exception_message in enqueued_event.error_message
