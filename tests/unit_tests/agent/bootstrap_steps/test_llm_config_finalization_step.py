# file: autobyteus/tests/unit_tests/agent/bootstrap_steps/test_llm_config_finalization_step.py
import pytest
import logging
from unittest.mock import MagicMock

# Import the module containing the class to be patched, to ensure we patch the correct reference
# No longer needed for LLMModel.__getitem__ patching, but good practice if other module-level items were patched.
# from autobyteus.agent.bootstrap_steps import llm_config_finalization_step as llm_config_finalization_step_module

from autobyteus.agent.bootstrap_steps.llm_config_finalization_step import LLMConfigFinalizationStep
from autobyteus.agent.events import AgentErrorEvent
from autobyteus.agent.context import AgentContext
from autobyteus.agent.context.agent_phase_manager import AgentPhaseManager
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.llm.models import LLMModel # Import for type hints and accessing real members
from autobyteus.llm.llm_factory import LLMFactory # To ensure models are initialized for test setup

@pytest.fixture
def llm_config_step_instance(): 
    return LLMConfigFinalizationStep()

@pytest.fixture(autouse=True)
def ensure_llm_factory_initialized():
    """Ensure LLMFactory is initialized before each test in this module, so real LLMModel members are available."""
    LLMFactory.ensure_initialized()

@pytest.mark.asyncio
async def test_llm_config_finalization_success(
    llm_config_step_instance: LLMConfigFinalizationStep, 
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager, 
    caplog,
    monkeypatch 
):
    processed_prompt = "This is the processed system prompt."
    agent_context.state.processed_system_prompt = processed_prompt
    
    # Use a real model name that is expected to be registered by LLMFactory
    # Ensure LLMFactory is initialized so that LLMModel.MISTRAL_LARGE_API exists
    # The autouse fixture ensure_llm_factory_initialized should handle this.
    real_model_member = LLMModel.MISTRAL_LARGE_API # Accessing a real model
    agent_context.config.llm_model_name = real_model_member.name # e.g., "MISTRAL_LARGE_API"
                                                            # The SUT will use this name for LLMModel[name]
    
    # Mock the default_config attribute of this specific, real LLMModel member instance
    mock_default_config_on_enum_member = MagicMock(spec=LLMConfig)
    dict_returned_by_to_dict = {"temperature": 0.7, "max_tokens": 100}
    mock_default_config_on_enum_member.to_dict.return_value = dict_returned_by_to_dict
    
    # Temporarily replace the default_config of the *actual* MISTRAL_LARGE_API model object
    monkeypatch.setattr(real_model_member, 'default_config', mock_default_config_on_enum_member)

    with caplog.at_level(logging.DEBUG): 
        success = await llm_config_step_instance.execute(agent_context, mock_phase_manager)

    if not success: # pragma: no cover
        print("Caplog text on failure in test_llm_config_finalization_success:")
        for record in caplog.records:
            print(f"{record.levelname} {record.name}:{record.lineno} - {record.getMessage()}")
            if record.exc_info:
                print(record.exc_text)

    assert success is True, f"LLMConfigFinalizationStep failed unexpectedly. Caplog: {caplog.text}"
    mock_phase_manager.notify_initializing_llm.assert_not_called() 
    assert f"Agent '{agent_context.agent_id}': Executing LLMConfigFinalizationStep." in caplog.text
    assert f"Agent '{agent_context.agent_id}': LLMConfig finalized and stored in state." in caplog.text
    
    final_config = agent_context.state.final_llm_config_for_creation
    assert isinstance(final_config, LLMConfig)
    assert final_config.system_message == processed_prompt
    assert final_config.temperature == 0.7 
    assert final_config.max_tokens == 100   
    agent_context.input_event_queues.enqueue_internal_system_event.assert_not_called()


@pytest.mark.asyncio
async def test_llm_config_finalization_with_custom_agent_config(
    llm_config_step_instance: LLMConfigFinalizationStep, 
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch 
):
    agent_context.state.processed_system_prompt = "Processed prompt."
    
    real_model_member = LLMModel.GPT_4o_API # Use another real model
    agent_context.config.llm_model_name = real_model_member.name
    
    custom_agent_llm_config = LLMConfig(temperature=0.9, max_tokens=500, top_p=0.8)
    agent_context.config.custom_llm_config = custom_agent_llm_config

    # Simulate that this real model member has no specific default_config (or its default_config is basic)
    # so that the LLMConfig() base is primarily used before merging custom_agent_llm_config.
    # If the real model has a substantial default_config, this test also implicitly tests merging over it.
    # For more precise control, we can mock its default_config to be None or a minimal LLMConfig().
    minimal_mock_default_config = MagicMock(spec=LLMConfig)
    minimal_mock_default_config.to_dict.return_value = {} # Simulate it contributing nothing or being None
    # Or directly:
    # monkeypatch.setattr(real_model_member, 'default_config', LLMConfig()) # A base LLMConfig
    # Or even None, if the step handles default_config being None on the model member:
    monkeypatch.setattr(real_model_member, 'default_config', None)


    success = await llm_config_step_instance.execute(agent_context, mock_phase_manager)

    assert success is True
    final_config = agent_context.state.final_llm_config_for_creation
    assert isinstance(final_config, LLMConfig)
    assert final_config.system_message == "Processed prompt."
    assert final_config.temperature == 0.9 
    assert final_config.max_tokens == 500   
    assert final_config.top_p == 0.8        


@pytest.mark.asyncio
async def test_llm_config_finalization_model_has_default_and_custom_agent_config(
    llm_config_step_instance: LLMConfigFinalizationStep, 
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch 
):
    agent_context.state.processed_system_prompt = "Processed prompt for merge."
    
    real_model_member = LLMModel.CLAUDE_3_7_SONNET_API # Use a real model
    agent_context.config.llm_model_name = real_model_member.name
    
    custom_agent_llm_config = LLMConfig(temperature=0.85, extra_params={"new_param":"custom_value"}) 
    agent_context.config.custom_llm_config = custom_agent_llm_config

    # Mock the default_config of this specific real model member
    mock_default_config_on_enum_member = MagicMock(spec=LLMConfig)
    dict_from_model_default_to_dict = {"temperature": 0.6, "max_tokens": 200, "extra_params": {"existing_param": "model_default"}}
    mock_default_config_on_enum_member.to_dict.return_value = dict_from_model_default_to_dict
    
    monkeypatch.setattr(real_model_member, 'default_config', mock_default_config_on_enum_member)

    success = await llm_config_step_instance.execute(agent_context, mock_phase_manager)

    assert success is True
    final_config = agent_context.state.final_llm_config_for_creation
    assert isinstance(final_config, LLMConfig)
    assert final_config.system_message == "Processed prompt for merge."
    
    assert final_config.temperature == 0.85 # Overridden by custom_agent_llm_config
    assert final_config.max_tokens == 200   # From model default's dict
    
    # Check extra_params merging (assuming AgentConfig.merge_with updates dicts)
    assert final_config.extra_params.get("new_param") == "custom_value"
    assert final_config.extra_params.get("existing_param") == "model_default"


@pytest.mark.asyncio
async def test_llm_config_finalization_failure_no_processed_prompt(
    llm_config_step_instance: LLMConfigFinalizationStep, 
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog
):
    agent_context.state.processed_system_prompt = None 

    with caplog.at_level(logging.ERROR):
        success = await llm_config_step_instance.execute(agent_context, mock_phase_manager)

    assert success is False
    assert "Critical failure during LLMConfig finalization: Processed system prompt not found" in caplog.text
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert "Processed system prompt not found" in enqueued_event.error_message

@pytest.mark.asyncio
async def test_llm_config_finalization_failure_invalid_model_name(
    llm_config_step_instance: LLMConfigFinalizationStep, 
    agent_context: AgentContext,
    mock_phase_manager: AgentPhaseManager,
    caplog,
    monkeypatch 
):
    agent_context.state.processed_system_prompt = "A valid prompt."
    invalid_model_name_for_test = "THIS_MODEL_DOES_NOT_EXIST_12345" # A name guaranteed not to be real
    agent_context.config.llm_model_name = invalid_model_name_for_test

    # No need to mock __getitem__ here if we expect it to fail for a truly non-existent model name.
    # The LLMModelMeta.__getitem__ will raise KeyError if LLMFactory.ensure_initialized()
    # has run and the model isn't found among its class attributes.
    # The autouse fixture ensure_llm_factory_initialized handles factory init.

    with caplog.at_level(logging.ERROR): 
        success = await llm_config_step_instance.execute(agent_context, mock_phase_manager)

    assert success is False
    
    expected_log_message_part = f"Invalid llm_model_name '{invalid_model_name_for_test}' in agent config"
    assert any(expected_log_message_part in record.message for record in caplog.records if record.levelno == logging.ERROR)

    expected_final_error_message_part = f"Invalid llm_model_name '{invalid_model_name_for_test}' for LLMConfig finalization."
    assert any(expected_final_error_message_part in record.message for record in caplog.records if record.levelno == logging.ERROR)
    
    agent_context.input_event_queues.enqueue_internal_system_event.assert_called_once()
    enqueued_event = agent_context.input_event_queues.enqueue_internal_system_event.call_args[0][0]
    assert isinstance(enqueued_event, AgentErrorEvent)
    assert enqueued_event.error_message == f"Invalid llm_model_name '{invalid_model_name_for_test}' for LLMConfig finalization."
    # The actual exception caught and stringified would be the ValueError that the step raises after catching KeyError
    assert enqueued_event.exception_details == str(ValueError(f"Invalid llm_model_name '{invalid_model_name_for_test}' for LLMConfig finalization."))
