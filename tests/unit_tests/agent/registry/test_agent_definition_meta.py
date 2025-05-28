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
    test_registry = AgentDefinitionRegistry()
    monkeypatch.setattr(
        'autobyteus.agent.registry.agent_registry.default_definition_registry_instance',
        test_registry
    )
    yield test_registry
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
            tool_names=["tool_x"],
            use_xml_tool_format=False # Explicitly set for test
        )
    
    assert len(registry) == 1
    retrieved_def = registry.get("AutoRegAgent", "TestRole")
    assert retrieved_def is definition
    assert retrieved_def.use_xml_tool_format is False # Verify new attribute
    
    expected_log_part = "Auto-registered AgentDefinition instance: 'AutoRegAgent' (Role: 'TestRole')"
    assert expected_log_part in caplog.text
    assert f"with key 'AutoRegAgent{AgentDefinitionRegistry._KEY_SEPARATOR}TestRole'" in caplog.text
    
    # Test default for use_xml_tool_format
    definition_default_xml = AgentDefinition(
        name="AutoRegAgentDefault",
        role="TestRoleDefault",
        description="Auto-registers",
        system_prompt="Behave.",
        tool_names=["tool_y"]
        # use_xml_tool_format uses default True
    )
    assert definition_default_xml.use_xml_tool_format is True
    assert registry.get("AutoRegAgentDefault", "TestRoleDefault") is definition_default_xml


def test_multiple_agent_definitions_auto_register(fresh_registry_for_meta_tests: AgentDefinitionRegistry):
    """Test that multiple distinct AgentDefinition instances are registered."""
    registry = fresh_registry_for_meta_tests
    
    def1 = AgentDefinition("AgentOne", "RoleA", "d1", "p1", [])
    def2 = AgentDefinition("AgentTwo", "RoleB", "d2", "p2", [], use_xml_tool_format=False)
    
    assert len(registry) == 2
    assert registry.get("AgentOne", "RoleA") is def1
    assert registry.get("AgentOne", "RoleA").use_xml_tool_format is True # Default
    assert registry.get("AgentTwo", "RoleB") is def2
    assert registry.get("AgentTwo", "RoleB").use_xml_tool_format is False


def test_auto_registration_on_init_failure(fresh_registry_for_meta_tests: AgentDefinitionRegistry):
    """
    Test that if AgentDefinition.__init__ fails, registration does not occur
    and the exception propagates.
    """
    registry = fresh_registry_for_meta_tests
    
    with pytest.raises(ValueError, match="AgentDefinition requires a non-empty string 'name'"):
        AgentDefinition(name="", role="InvalidRole", description="d", system_prompt="p", tool_names=[])
        
    assert len(registry) == 0, "Registry should be empty if __init__ failed before registration."

    # Test invalid type for use_xml_tool_format
    with pytest.raises(ValueError, match="requires 'use_xml_tool_format' to be a boolean if provided"):
        AgentDefinition(name="ValidName", role="ValidRole", description="d", system_prompt="p", tool_names=[], use_xml_tool_format="not_a_bool") # type: ignore
    assert len(registry) == 0


@patch('autobyteus.agent.registry.agent_definition_meta.logger') 
def test_auto_registration_failure_if_registry_register_fails(
    mock_meta_logger: MagicMock, 
    fresh_registry_for_meta_tests: AgentDefinitionRegistry
):
    registry = fresh_registry_for_meta_tests
    simulated_error = RuntimeError("Simulated registry.register() failure")
    original_register_method = registry.register 
    registry.register = MagicMock(side_effect=simulated_error)

    definition = None
    try:
        definition = AgentDefinition("FailRegAgent", "TestRole", "d", "p", [])
    except Exception: 
        pytest.fail("AgentDefinition instantiation should not fail if only registration fails.")
    finally:
        registry.register = original_register_method 

    assert definition is not None
    assert definition.name == "FailRegAgent"
    assert len(registry._definitions) == 0
    
    mock_meta_logger.error.assert_called_once()
    logged_message = mock_meta_logger.error.call_args[0][0]
    logged_exc_info = mock_meta_logger.error.call_args.kwargs.get('exc_info', False)
    assert "An unexpected error occurred during auto-registration of AgentDefinition 'FailRegAgent'" in logged_message
    assert str(simulated_error) in logged_message 
    assert logged_exc_info is True 


@patch('autobyteus.agent.registry.agent_definition_meta.logger')
def test_auto_registration_skipped_if_default_registry_is_none(mock_meta_logger: MagicMock, monkeypatch):
    monkeypatch.setattr(
        'autobyteus.agent.registry.agent_registry.default_definition_registry_instance',
        None
    )
    definition = AgentDefinition("NoRegAgent", "NoRegRole", "d", "p", [])
    assert definition is not None
    assert definition.name == "NoRegAgent"
    
    error_logged = False
    for call_arg_list in mock_meta_logger.error.call_args_list:
        args, _ = call_arg_list
        if "Default AgentDefinitionRegistry instance (default_definition_registry_instance) is None" in args[0]:
            error_logged = True
            break
    assert error_logged, "Expected log for None default_definition_registry_instance was not found."


def test_metaclass_does_not_interfere_with_definition_attributes(fresh_registry_for_meta_tests):
    registry = fresh_registry_for_meta_tests
    custom_sys_procs = ["CustomSysProc"]
    custom_llm_resp_procs = ["CustomRespProc"]

    definition = AgentDefinition(
        name="AttrAgent",
        role="AttrRole",
        description="Desc",
        system_prompt="Prompt",
        tool_names=["tool_y"],
        input_processor_names=["proc1"],
        llm_response_processor_names=custom_llm_resp_procs,
        system_prompt_processor_names=custom_sys_procs,
        use_xml_tool_format=False
    )
    
    assert definition.name == "AttrAgent"
    assert definition.role == "AttrRole"
    assert definition.description == "Desc"
    assert definition.system_prompt == "Prompt"
    assert definition.tool_names == ["tool_y"]
    assert definition.input_processor_names == ["proc1"]
    assert definition.llm_response_processor_names == custom_llm_resp_procs
    assert definition.system_prompt_processor_names == custom_sys_procs
    assert definition.use_xml_tool_format is False # Check new attribute
    
    default_def = AgentDefinition("DefaultProcAgent", "RoleDef", "d", "p", [])
    assert default_def.llm_response_processor_names == AgentDefinition.DEFAULT_LLM_RESPONSE_PROCESSORS
    assert default_def.system_prompt_processor_names == AgentDefinition.DEFAULT_SYSTEM_PROMPT_PROCESSORS
    assert default_def.use_xml_tool_format is True # Check default
    
    assert len(registry) == 2
    assert registry.get("AttrAgent", "AttrRole") is definition
    assert registry.get("DefaultProcAgent", "RoleDef") is default_def
