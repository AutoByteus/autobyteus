import pytest
import logging
from unittest.mock import patch, MagicMock

# Classes to be tested / used
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.registry.agent_definition_meta import AgentDefinitionMeta
from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry

# This is the global instance that AgentDefinitionMeta will try to use
# from autobyteus.agent.registry.agent_registry import default_definition_registry_instance
# We will patch this path within the tests.

@pytest.fixture(autouse=True)
def fresh_registry_for_meta_tests(monkeypatch):
    """
    Ensures that for each test using this fixture, the AgentDefinitionMeta
    attempts to register with a fresh, isolated AgentDefinitionRegistry instance.
    It also clears this fresh registry before each test.
    """
    # Create a fresh registry instance for tests
    test_registry = AgentDefinitionRegistry()

    # Patch the location where AgentDefinitionMeta imports default_definition_registry_instance.
    # This is the actual source of the 'default_definition_registry_instance' name.
    monkeypatch.setattr(
        'autobyteus.agent.registry.agent_registry.default_definition_registry_instance',
        test_registry
    )
    
    # Yield the test_registry so tests can access it if needed for assertions
    yield test_registry
    
    # Teardown: clear the test_registry after the test if needed, though a new one is made each time.
    test_registry.clear()


def test_agent_definition_auto_registers(fresh_registry_for_meta_tests: AgentDefinitionRegistry, caplog):
    """Test that creating an AgentDefinition instance automatically registers it."""
    registry = fresh_registry_for_meta_tests
    assert len(registry) == 0

    with caplog.at_level(logging.INFO):
        definition = AgentDefinition(
            name="AutoRegAgent",
            role="TestRole",
            description="Auto-registers",
            system_prompt="Behave.",
            tool_names=["tool_x"]
        )
    
    assert len(registry) == 1
    retrieved_def = registry.get("AutoRegAgent", "TestRole")
    assert retrieved_def is definition
    
    expected_log_part = "Auto-registered AgentDefinition instance: 'AutoRegAgent' (Role: 'TestRole')"
    assert expected_log_part in caplog.text
    assert f"with key 'AutoRegAgent{AgentDefinitionRegistry._KEY_SEPARATOR}TestRole'" in caplog.text


def test_multiple_agent_definitions_auto_register(fresh_registry_for_meta_tests: AgentDefinitionRegistry):
    """Test that multiple distinct AgentDefinition instances are registered."""
    registry = fresh_registry_for_meta_tests
    
    def1 = AgentDefinition("AgentOne", "RoleA", "d1", "p1", [])
    def2 = AgentDefinition("AgentTwo", "RoleB", "d2", "p2", [])
    
    assert len(registry) == 2
    assert registry.get("AgentOne", "RoleA") is def1
    assert registry.get("AgentTwo", "RoleB") is def2

def test_auto_registration_on_init_failure(fresh_registry_for_meta_tests: AgentDefinitionRegistry):
    """
    Test that if AgentDefinition.__init__ fails, registration does not occur
    and the exception propagates.
    """
    registry = fresh_registry_for_meta_tests
    
    with pytest.raises(ValueError, match="AgentDefinition requires a non-empty string 'name'"):
        # This will fail in AgentDefinition.__init__
        AgentDefinition(name="", role="InvalidRole", description="d", system_prompt="p", tool_names=[])
        
    assert len(registry) == 0, "Registry should be empty if __init__ failed before registration."

@patch('autobyteus.agent.registry.agent_definition_meta.logger') # Patch logger inside AgentDefinitionMeta
def test_auto_registration_failure_if_registry_register_fails(
    mock_meta_logger: MagicMock, 
    fresh_registry_for_meta_tests: AgentDefinitionRegistry
):
    """
    Test graceful handling if the registry's register method itself fails.
    The instance should still be created and returned.
    """
    registry = fresh_registry_for_meta_tests
    
    # Mock the register method of our test_registry to raise an error
    simulated_error = RuntimeError("Simulated registry.register() failure")
    
    # Ensure the mocked register is on the correct registry instance that the meta will use
    registry.register = MagicMock(side_effect=simulated_error)


    definition = None
    try:
        definition = AgentDefinition("FailRegAgent", "TestRole", "d", "p", [])
    except Exception: # pragma: no cover
        pytest.fail("AgentDefinition instantiation should not fail if only registration fails.")

    assert definition is not None, "AgentDefinition instance should still be created."
    assert definition.name == "FailRegAgent"
    # The registry.register was mocked to fail, so the item count should reflect that.
    # If register fails, the item is not added.
    assert len(registry._definitions) == 0, "Registry's internal definitions dict should be empty." 
    
    mock_meta_logger.error.assert_called_once()
    
    # Extract the logged message and exception from the call_args
    # call_args is a tuple, first element is args, second is kwargs
    # For logger.error(msg, exc_info=True), msg is args[0], and exc_info=True implies the exception is logged.
    # We need to check the first positional argument of the logger call for the message.
    logged_message = mock_meta_logger.error.call_args[0][0]
    logged_exc_info = mock_meta_logger.error.call_args.kwargs.get('exc_info', False)

    assert "An unexpected error occurred during auto-registration of AgentDefinition 'FailRegAgent'" in logged_message
    assert str(simulated_error) in logged_message # Check if the original error message is part of the log
    assert logged_exc_info is True # Check that exc_info=True was used


@patch('autobyteus.agent.registry.agent_definition_meta.logger')
def test_auto_registration_skipped_if_default_registry_is_none(mock_meta_logger: MagicMock, monkeypatch):
    """
    Test that registration is skipped and an error is logged if the default
    registry instance is None when AgentDefinitionMeta tries to use it.
    """
    # Make the default_definition_registry_instance (as imported by the metaclass) None
    monkeypatch.setattr(
        'autobyteus.agent.registry.agent_registry.default_definition_registry_instance',
        None
    )
    
    definition = AgentDefinition("NoRegAgent", "NoRegRole", "d", "p", [])

    assert definition is not None
    assert definition.name == "NoRegAgent"
    
    # Check for the specific error log about the registry being None
    error_logged = False
    for call_arg_list in mock_meta_logger.error.call_args_list:
        if "Default AgentDefinitionRegistry instance (default_definition_registry_instance) is None" in call_arg_list[0][0]:
            error_logged = True
            break
    assert error_logged, "Expected log for None default_definition_registry_instance was not found."


def test_metaclass_does_not_interfere_with_definition_attributes(fresh_registry_for_meta_tests):
    """Ensure standard attribute access and class properties are unaffected."""
    registry = fresh_registry_for_meta_tests
    
    definition = AgentDefinition(
        name="AttrAgent",
        role="AttrRole",
        description="Desc",
        system_prompt="Prompt",
        tool_names=["tool_y"],
        input_processor_names=["proc1"],
        llm_response_processor_names=["resp_proc1"]
    )
    
    assert definition.name == "AttrAgent"
    assert definition.role == "AttrRole"
    assert definition.description == "Desc"
    assert definition.system_prompt == "Prompt"
    assert definition.tool_names == ["tool_y"]
    assert definition.input_processor_names == ["proc1"]
    assert definition.llm_response_processor_names == ["resp_proc1"]
    assert AgentDefinition.DEFAULT_LLM_RESPONSE_PROCESSORS == ["xml_tool_usage"]
    
    assert len(registry) == 1
    assert registry.get("AttrAgent", "AttrRole") is definition
