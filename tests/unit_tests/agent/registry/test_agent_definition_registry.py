# file: autobyteus/tests/unit_tests/agent/registry/test_agent_definition_registry.py
import pytest
import logging
from unittest.mock import patch

# This test file previously tested AgentDefinitionRegistry.
# Since the concept of a definition/specification registry has been removed from AgentRegistry,
# this test file is repurposed to perform additional validation of the AgentSpecification class.

from autobyteus.agent.registry.agent_specification import AgentSpecification

def test_agent_specification_with_empty_and_none_optional_lists():
    """Test AgentSpecification initialization with empty or None lists for optional fields."""
    # Test with empty lists
    spec_empty = AgentSpecification(
        name="TestAgent1",
        role="Worker",
        description="Desc",
        system_prompt="Prompt",
        tool_names=[],
        input_processor_names=[],
        llm_response_processor_names=[],
        system_prompt_processor_names=[]
    )
    assert spec_empty.input_processor_names == []
    assert spec_empty.llm_response_processor_names == []
    assert spec_empty.system_prompt_processor_names == []

    # Test with None, which should default to empty lists or default processors
    spec_none = AgentSpecification(
        name="TestAgent2",
        role="Analyst",
        description="Desc",
        system_prompt="Prompt",
        tool_names=[],
        input_processor_names=None,
        llm_response_processor_names=None,
        system_prompt_processor_names=None
    )
    assert spec_none.input_processor_names == []
    assert spec_none.llm_response_processor_names == AgentSpecification.DEFAULT_LLM_RESPONSE_PROCESSORS
    assert spec_none.system_prompt_processor_names == AgentSpecification.DEFAULT_SYSTEM_PROMPT_PROCESSORS

def test_agent_specification_use_xml_tool_format_flag():
    """Test the 'use_xml_tool_format' flag in AgentSpecification."""
    # Test default value
    spec_default = AgentSpecification(
        name="XMLDefault", role="Role", description="d", system_prompt="p", tool_names=[]
    )
    assert spec_default.use_xml_tool_format is True

    # Test explicit True
    spec_true = AgentSpecification(
        name="XMLExplicit", role="Role", description="d", system_prompt="p", tool_names=[], use_xml_tool_format=True
    )
    assert spec_true.use_xml_tool_format is True

    # Test explicit False
    spec_false = AgentSpecification(
        name="JSONExplicit", role="Role", description="d", system_prompt="p", tool_names=[], use_xml_tool_format=False
    )
    assert spec_false.use_xml_tool_format is False
