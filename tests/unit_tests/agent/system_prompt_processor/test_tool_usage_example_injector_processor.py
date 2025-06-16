# file: autobyteus/tests/unit_tests/agent/system_prompt_processor/test_tool_usage_example_injector_processor.py
from unittest.mock import patch, MagicMock
import pytest
import logging
import json 
from typing import Dict, Optional, Any

from autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor import ToolUsageExampleInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.registry import ToolDefinition
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from ._test_helpers import MockTool 

# Helper to create mock definitions
def create_mock_example_definition(name, xml_example, json_example):
    mock_def = MagicMock(spec=ToolDefinition)
    mock_def.name = name # For logging/error messages
    mock_def.get_usage_xml_example.return_value = xml_example
    mock_def.get_usage_json_example.return_value = json_example
    return mock_def

@pytest.fixture
def mock_context_factory():
    """
    A factory to create a mock AgentContext, with the correct nested structure.
    """
    def _factory(use_xml: bool, provider: LLMProvider):
        # Create mocks for the nested objects
        mock_model = MagicMock(spec=LLMModel)
        mock_model.provider = provider

        mock_llm_instance = MagicMock(spec=BaseLLM)
        mock_llm_instance.model = mock_model

        mock_config = MagicMock(spec=AgentConfig)
        mock_config.use_xml_tool_format = use_xml
        
        # Create the main context mock
        context = MagicMock(spec=AgentContext)
        context.agent_id = "test_agent_123"
        context.config = mock_config
        context.llm_instance = mock_llm_instance
        
        return context
    return _factory


def test_tool_example_injector_get_name():
    processor = ToolUsageExampleInjectorProcessor()
    assert processor.get_name() == "ToolUsageExampleInjector"

def test_process_prompt_without_placeholder(mock_context_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "This is a system prompt without the examples placeholder."
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt

def test_process_with_placeholder_and_no_tools(mock_context_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "Tool examples: {{tool_examples}}"
    
    with caplog.at_level(logging.INFO):
        processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert f"{processor.get_name()}: No tools available for agent '{mock_context.agent_id}'." in caplog.text
    expected_prompt = f"Tool examples: {processor.DEFAULT_NO_TOOLS_MESSAGE}"
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor.default_tool_registry')
def test_process_with_one_tool_xml_format(mock_registry, mock_context_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "Example: {{tool_examples}}"
    
    tool_instance = MockTool(name="MyTool", description="My Tool")
    tools: Dict[str, BaseTool] = {"MyTool": tool_instance}
    
    expected_xml_example = '<tool_call name="MyTool">...</tool_call>'
    mock_def = create_mock_example_definition("MyTool", expected_xml_example, {})
    mock_registry.get_tool_definition.return_value = mock_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    expected_injection = f"{processor.XML_EXAMPLES_HEADER}<tool_calls>\n{expected_xml_example}\n</tool_calls>"
    assert processed_prompt == original_prompt.replace("{{tool_examples}}", expected_injection)
    assert "{{tool_examples}}" not in processed_prompt
    mock_def.get_usage_xml_example.assert_called_once_with(provider=LLMProvider.ANTHROPIC)

@patch('autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor.default_tool_registry')
def test_process_with_one_tool_json_format(mock_registry, mock_context_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Example: {{tool_examples}}"
    
    tool_instance = MockTool(name="MyTool", description="My Tool")
    tools: Dict[str, BaseTool] = {"MyTool": tool_instance}
    
    expected_json_example_obj = {"tool_name": "MyTool", "arguments": {"param": "value"}}
    mock_def = create_mock_example_definition("MyTool", "", expected_json_example_obj)
    mock_registry.get_tool_definition.return_value = mock_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    expected_json_example_str = json.dumps(expected_json_example_obj, indent=2)
    expected_injection = f"{processor.JSON_EXAMPLES_HEADER}[\n{expected_json_example_str}\n]"
    
    assert processed_prompt == original_prompt.replace("{{tool_examples}}", expected_injection)
    assert "{{tool_examples}}" not in processed_prompt
    mock_def.get_usage_json_example.assert_called_once_with(provider=LLMProvider.OPENAI)

@patch('autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor.default_tool_registry')
def test_process_failure_to_generate_example_for_one_tool_xml_format(mock_registry, mock_context_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    prompt = "Examples: {{tool_examples}}"

    tool_alpha = MockTool(name="AlphaTool", description="Alpha desc")
    tool_beta = MockTool(name="BetaTool", description="Beta desc")
    tools: Dict[str, BaseTool] = {"AlphaTool": tool_alpha, "BetaTool": tool_beta}

    # Setup mocks
    mock_alpha_def = create_mock_example_definition("AlphaTool", None, None)
    mock_alpha_def.get_usage_xml_example.side_effect = RuntimeError("Simulated XML failure")
    
    beta_xml_example = '<tool_call name="BetaTool" />'
    mock_beta_def = create_mock_example_definition("BetaTool", beta_xml_example, {})

    mock_registry.get_tool_definition.side_effect = lambda name: mock_alpha_def if name == "AlphaTool" else mock_beta_def

    # Process
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    # Assert
    assert "Failed to generate XML example for tool 'AlphaTool'" in caplog.text
    assert "<!-- Error generating XML example for tool: AlphaTool -->" in processed_prompt
    assert beta_xml_example in processed_prompt 
    assert "{{tool_examples}}" not in processed_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor.default_tool_registry')
def test_process_failure_to_generate_example_for_one_tool_json_format(mock_registry, mock_context_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    prompt = "Examples: {{tool_examples}}"

    tool_alpha = MockTool(name="AlphaTool", description="Alpha desc")
    tool_beta = MockTool(name="BetaTool", description="Beta desc")
    tools: Dict[str, BaseTool] = {"AlphaTool": tool_alpha, "BetaTool": tool_beta}

    # Setup mocks
    mock_alpha_def = create_mock_example_definition("AlphaTool", None, None)
    mock_alpha_def.get_usage_json_example.side_effect = RuntimeError("Simulated JSON failure")
    
    beta_json_example = {"tool_name": "BetaTool", "arguments": {}}
    mock_beta_def = create_mock_example_definition("BetaTool", "", beta_json_example)

    mock_registry.get_tool_definition.side_effect = lambda name: mock_alpha_def if name == "AlphaTool" else mock_beta_def

    # Process
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)
    
    # Assert
    assert "Failed to generate JSON example for tool 'AlphaTool'" in caplog.text
    assert "// Error generating JSON example for tool: AlphaTool" in processed_prompt
    
    beta_json_example_str = json.dumps(beta_json_example, indent=2)
    assert beta_json_example_str in processed_prompt
    
    assert "{{tool_examples}}" not in processed_prompt
