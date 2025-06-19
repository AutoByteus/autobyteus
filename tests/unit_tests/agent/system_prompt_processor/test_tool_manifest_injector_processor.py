# file: autobyteus/tests/unit_tests/agent/system_prompt_processor/test_tool_manifest_injector_processor.py
import pytest
import logging
import json
from typing import Dict
from unittest.mock import MagicMock, patch

from autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor import ToolManifestInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.registry import ToolDefinition
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider

# Helper to create mock definitions for testing
def create_mock_tool_definition(name, xml_schema, xml_example, json_schema, json_example):
    mock_def = MagicMock(spec=ToolDefinition)
    mock_def.name = name
    mock_def.get_usage_xml.return_value = xml_schema
    mock_def.get_usage_xml_example.return_value = xml_example
    mock_def.get_usage_json.return_value = json_schema
    mock_def.get_usage_json_example.return_value = json_example
    return mock_def

@pytest.fixture
def mock_context_factory():
    """A factory fixture to create a mock AgentContext for testing."""
    def _factory(use_xml: bool, provider: LLMProvider):
        mock_model = MagicMock(spec=LLMModel)
        mock_model.provider = provider
        mock_llm_instance = MagicMock(spec=BaseLLM)
        mock_llm_instance.model = mock_model
        mock_config = MagicMock(spec=AgentConfig)
        mock_config.use_xml_tool_format = use_xml
        context = MagicMock(spec=AgentContext)
        context.agent_id = "test_agent_123"
        context.config = mock_config
        context.llm_instance = mock_llm_instance
        return context
    return _factory

@pytest.fixture
def processor() -> ToolManifestInjectorProcessor:
    """Provides an instance of the processor for tests."""
    return ToolManifestInjectorProcessor()

def test_get_name(processor: ToolManifestInjectorProcessor):
    """Tests that the processor returns the correct name."""
    assert processor.get_name() == "ToolManifestInjector"

def test_process_prompt_without_placeholder(processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests that the prompt is unchanged if the placeholder is missing."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "This is a simple prompt."
    processed_prompt = processor.process(original_prompt, {"SomeTool": MagicMock(spec=BaseTool)}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt

def test_process_with_no_tools(processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that a 'no tools' message is injected when no tools are provided."""
    caplog.set_level(logging.INFO)
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    prompt_with_placeholder = "Tools: {{tools}}"
    processed_prompt = processor.process(prompt_with_placeholder, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated" in caplog.text
    assert "No tools available for this agent." in processed_prompt

def test_process_only_placeholder_prepends_default_prefix(processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests that the default prefix is added when the prompt only contains the placeholder."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    prompt_only_placeholder = "  {{tools}}  "
    processed_prompt = processor.process(prompt_only_placeholder, {}, mock_context.agent_id, mock_context)
    
    assert processed_prompt.startswith(ToolManifestInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT)

@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_with_one_tool_xml_format(mock_registry, processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests successful injection of one tool's manifest in XML format."""
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    
    schema_xml = "<tool name='AlphaTool'><arguments/></tool>"
    example_xml = "<tool name='AlphaTool'><arguments><arg name='p'>v</arg></arguments></tool>"
    mock_def = create_mock_tool_definition("AlphaTool", schema_xml, example_xml, {}, {})
    mock_registry.get_tool_definition.return_value = mock_def

    tools = {"AlphaTool": MagicMock(spec=BaseTool)}
    prompt = "Use these tools: {{tools}}"
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    expected_block = f"{processor.SCHEMA_HEADER}\n{schema_xml}\n\n{processor.EXAMPLE_HEADER}\n{example_xml}"
    assert expected_block in processed_prompt
    assert "{{tools}}" not in processed_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_with_multiple_tools_json_format(mock_registry, processor: ToolManifestInjectorProcessor, mock_context_factory):
    """Tests successful injection of multiple tools' manifests in JSON format."""
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)

    schema_json_alpha = {"name": "AlphaTool", "description": "A"}
    example_json_alpha = {"name": "AlphaTool", "arguments": {}}
    mock_def_alpha = create_mock_tool_definition("AlphaTool", "", "", schema_json_alpha, example_json_alpha)

    schema_json_beta = {"name": "BetaTool", "description": "B"}
    example_json_beta = {"name": "BetaTool", "arguments": {"p": "v"}}
    mock_def_beta = create_mock_tool_definition("BetaTool", "", "", schema_json_beta, example_json_beta)
    
    mock_registry.get_tool_definition.side_effect = lambda name: mock_def_alpha if name == "AlphaTool" else mock_def_beta
    
    tools = {"AlphaTool": MagicMock(spec=BaseTool), "BetaTool": MagicMock(spec=BaseTool)}
    prompt = "Use these tools: {{tools}}"
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    # Check that both manifests are present as JSON objects within a list
    assert '"tool_definition": {"name": "AlphaTool", "description": "A"}' in processed_prompt
    assert '"example_call": {"name": "AlphaTool", "arguments": {}}' in processed_prompt
    assert '"tool_definition": {"name": "BetaTool", "description": "B"}' in processed_prompt
    assert '"example_call": {"name": "BetaTool", "arguments": {"p": "v"}}' in processed_prompt
    
    # Verify it's a valid JSON array
    json_part = processed_prompt.split("\n", 1)[1]
    parsed_json = json.loads(json_part)
    assert isinstance(parsed_json, list)
    assert len(parsed_json) == 2

@patch('autobyteus.agent.system_prompt_processor.tool_manifest_injector_processor.default_tool_registry')
def test_process_with_tool_generation_error(mock_registry, processor: ToolManifestInjectorProcessor, mock_context_factory, caplog):
    """Tests that processing continues if one tool fails to generate its manifest."""
    caplog.set_level(logging.ERROR)
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)

    # Tool that will fail
    mock_def_alpha = create_mock_tool_definition("AlphaTool", "", "", {}, {})
    mock_def_alpha.get_usage_xml.side_effect = RuntimeError("Generation Failed")
    
    # Tool that will succeed
    schema_xml_beta = "<tool name='BetaTool' />"
    example_xml_beta = "<tool name='BetaTool'><arguments/></tool>"
    mock_def_beta = create_mock_tool_definition("BetaTool", schema_xml_beta, example_xml_beta, {}, {})
    
    mock_registry.get_tool_definition.side_effect = lambda name: mock_def_alpha if name == "AlphaTool" else mock_def_beta
    
    tools = {"AlphaTool": MagicMock(spec=BaseTool), "BetaTool": MagicMock(spec=BaseTool)}
    prompt = "Use these tools: {{tools}}"
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    # Assert that the error was logged
    assert "Failed to process tool 'AlphaTool' for prompt injection" in caplog.text
    # Assert that the successful tool's manifest is still present
    assert schema_xml_beta in processed_prompt
    assert example_xml_beta in processed_prompt
    # Assert that the failed tool's manifest is not present
    assert "AlphaTool" not in processed_prompt
