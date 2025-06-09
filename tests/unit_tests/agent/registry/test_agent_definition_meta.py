# file: autobyteus/tests/unit_tests/agent/registry/test_agent_definition_meta.py
import pytest
import logging
from unittest.mock import patch, MagicMock

# This test file previously tested AgentDefinitionMeta and auto-registration.
# Since AgentSpecification is now a plain class without a metaclass for auto-registration,
# this test file is repurposed to perform basic validation of the AgentSpecification class itself.

from autobyteus.agent.registry.agent_specification import AgentSpecification

def test_agent_specification_initialization():
    """Test successful initialization of AgentSpecification with all parameters."""
    spec = AgentSpecification(
        name="TestSpec",
        role="Tester",
        description="A test specification.",
        system_prompt="You are a test agent.",
        tool_names=["tool1", "tool2"],
        input_processor_names=["proc1"],
        llm_response_processor_names=["resp_proc1"],
        system_prompt_processor_names=["sys_proc1"],
        use_xml_tool_format=False
    )
    assert spec.name == "TestSpec"
    assert spec.role == "Tester"
    assert spec.description == "A test specification."
    assert spec.system_prompt == "You are a test agent."
    assert spec.tool_names == ["tool1", "tool2"]
    assert spec.input_processor_names == ["proc1"]
    assert spec.llm_response_processor_names == ["resp_proc1"]
    assert spec.system_prompt_processor_names == ["sys_proc1"]
    assert spec.use_xml_tool_format is False

def test_agent_specification_default_values():
    """Test default values for optional parameters in AgentSpecification."""
    spec = AgentSpecification(
        name="DefaultSpec",
        role="DefaultRole",
        description="Default description",
        system_prompt="Default prompt",
        tool_names=[]
    )
    assert spec.input_processor_names == []
    assert spec.llm_response_processor_names == AgentSpecification.DEFAULT_LLM_RESPONSE_PROCESSORS
    assert spec.system_prompt_processor_names == AgentSpecification.DEFAULT_SYSTEM_PROMPT_PROCESSORS
    assert spec.use_xml_tool_format is True # Check default

def test_agent_specification_repr():
    """Test the __repr__ method of AgentSpecification."""
    spec = AgentSpecification(
        name="ReprSpec",
        role="ReprRole",
        description="desc",
        system_prompt="prompt",
        tool_names=[],
        use_xml_tool_format=False
    )
    expected_repr = "AgentSpecification(name='ReprSpec', role='ReprRole', use_xml_tool_format=False)"
    assert repr(spec) == expected_repr

def test_agent_specification_can_be_instantiated_without_error():
    """A simple sanity check that ensures the class can be instantiated without runtime errors."""
    try:
        AgentSpecification(
            name="SanityCheck",
            role="Checker",
            description="Sanity check",
            system_prompt="This is a test.",
            tool_names=[]
        )
    except Exception as e:
        pytest.fail(f"AgentSpecification instantiation failed with an unexpected exception: {e}")
