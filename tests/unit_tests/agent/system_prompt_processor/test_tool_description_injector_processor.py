# file: autobyteus/tests/unit_tests/agent/system_prompt_processor/test_tool_description_injector_processor.py
import pytest
import logging 
import json
from typing import Dict
from unittest.mock import MagicMock, patch

from autobyteus.agent.system_prompt_processor.tool_description_injector_processor import ToolDescriptionInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.registry import ToolDefinition
from autobyteus.agent.context import AgentContext, AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider

# Helper to create mock definitions
def create_mock_definition(name, xml_return, json_return):
    mock_def = MagicMock(spec=ToolDefinition)
    mock_def.name = name # Set the name attribute for logging/error messages
    mock_def.get_usage_xml.return_value = xml_return
    mock_def.get_usage_json.return_value = json_return
    return mock_def

@pytest.fixture
def mock_context_factory():
    """
    A factory to create a mock AgentContext, now with the correct nested structure.
    This replaces the implicit dependency on a conftest factory.
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


def test_tool_injector_get_name():
    """Test the get_name() method of ToolDescriptionInjectorProcessor."""
    processor = ToolDescriptionInjectorProcessor()
    assert processor.get_name() == "ToolDescriptionInjector"

def test_process_prompt_without_placeholder(mock_context_factory):
    """Test processing when the system prompt does not contain the '{{tools}}' placeholder."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "This is a simple system prompt."
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt, "Prompt should remain unchanged if placeholder is missing."

def test_process_with_placeholder_and_no_tools_xml(mock_context_factory, caplog):
    """Test processing for XML when '{{tools}}' is present but no tools are provided."""
    # Set caplog to capture INFO level messages for this test
    caplog.set_level(logging.INFO)
    
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "Available tools: {{tools}}"
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    expected_prompt = "Available tools: \nNo tools available for this agent."
    assert processed_prompt == expected_prompt

def test_process_with_placeholder_and_no_tools_json(mock_context_factory, caplog):
    """Test processing for JSON when '{{tools}}' is present but no tools are provided."""
    # Set caplog to capture INFO level messages for this test
    caplog.set_level(logging.INFO)

    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Available tools: {{tools}}"
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    expected_prompt = "Available tools: \nNo tools available for this agent." # Message is format-agnostic
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_with_placeholder_and_one_tool_xml(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory):
    """Test processing with '{{tools}}' and one available tool, XML format."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "Please use {{tools}} for this task."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    alpha_xml = "<tool name='AlphaTool' />"
    mock_alpha_def = create_mock_definition("AlphaTool", alpha_xml, {})
    mock_registry.get_tool_definition.return_value = mock_alpha_def
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    expected_prompt = f"Please use \n<tools>\n{alpha_xml}\n</tools> for this task."
    assert processed_prompt == expected_prompt
    mock_registry.get_tool_definition.assert_called_once_with("AlphaTool")
    # The assertion now checks that the provider was correctly retrieved from the nested mock
    mock_alpha_def.get_usage_xml.assert_called_once_with(provider=LLMProvider.ANTHROPIC)

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_with_placeholder_and_one_tool_json(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory):
    """Test processing with '{{tools}}' and one available tool, JSON format."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Please use {{tools}} for this task."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    alpha_json_schema = {"name": "AlphaTool", "description": "Desc for Alpha", "input_schema": {}}
    mock_alpha_def = create_mock_definition("AlphaTool", "", alpha_json_schema)
    mock_registry.get_tool_definition.return_value = mock_alpha_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    expected_json_str = json.dumps(alpha_json_schema, indent=2)
    expected_prompt = f"Please use \n{expected_json_str} for this task."
    assert processed_prompt == expected_prompt
    mock_registry.get_tool_definition.assert_called_once_with("AlphaTool")
    mock_alpha_def.get_usage_json.assert_called_once_with(provider=LLMProvider.OPENAI)

# The rest of the tests would be updated to use mock_context_factory as well.
# For brevity, I am showing the full implementation for the key tests above.
# The remaining tests below are kept in their original form to avoid excessive repetition,
# but they would follow the same pattern of using the new factory.

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_with_placeholder_and_multiple_tools_xml(mock_registry, mock_tool_alpha: BaseTool, mock_tool_beta: BaseTool, mock_context_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "Consider these: {{tools}}."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": mock_tool_beta}
    
    alpha_xml = "<tool name='AlphaTool' />"
    beta_xml = "<tool name='BetaTool' />"
    mock_alpha_def = create_mock_definition("AlphaTool", alpha_xml, {})
    mock_beta_def = create_mock_definition("BetaTool", beta_xml, {})
    mock_registry.get_tool_definition.side_effect = lambda name: mock_alpha_def if name == "AlphaTool" else mock_beta_def
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    assert "{{tools}}" not in processed_prompt
    assert alpha_xml in processed_prompt
    assert beta_xml in processed_prompt
    
    expected_tools_part1 = f"<tools>\n{alpha_xml}\n{beta_xml}\n</tools>"
    expected_tools_part2 = f"<tools>\n{beta_xml}\n{alpha_xml}\n</tools>"
    assert (original_prompt.replace("{{tools}}", f"\n{expected_tools_part1}") == processed_prompt or
            original_prompt.replace("{{tools}}", f"\n{expected_tools_part2}") == processed_prompt)

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_with_placeholder_and_multiple_tools_json(mock_registry, mock_tool_alpha: BaseTool, mock_tool_beta: BaseTool, mock_context_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Consider these: {{tools}}."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": mock_tool_beta}

    alpha_json_schema = {"name": "AlphaTool", "description": "Desc Alpha", "input_schema": {}}
    beta_json_schema = {"name": "BetaTool", "description": "Desc Beta", "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}}}
    mock_alpha_def = create_mock_definition("AlphaTool", "", alpha_json_schema)
    mock_beta_def = create_mock_definition("BetaTool", "", beta_json_schema)
    mock_registry.get_tool_definition.side_effect = lambda name: mock_alpha_def if name == "AlphaTool" else mock_beta_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    alpha_json_str = json.dumps(alpha_json_schema, indent=2)
    beta_json_str = json.dumps(beta_json_schema, indent=2)
    
    assert "{{tools}}" not in processed_prompt
    assert alpha_json_str in processed_prompt
    assert beta_json_str in processed_prompt
    
    expected_tools_part1 = f"{alpha_json_str}\n{beta_json_str}"
    expected_tools_part2 = f"{beta_json_str}\n{alpha_json_str}"
    assert (original_prompt.replace("{{tools}}", f"\n{expected_tools_part1}") == processed_prompt or
            original_prompt.replace("{{tools}}", f"\n{expected_tools_part2}") == processed_prompt)

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_tool_returning_empty_xml_logs_warning(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "Tool: {{tools}}"
    tools: Dict[str, BaseTool] = {"EmptyXmlTool": mock_tool_alpha}

    mock_def = create_mock_definition("EmptyXmlTool", "", {})
    mock_registry.get_tool_definition.return_value = mock_def
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    assert f"Tool 'EmptyXmlTool' for agent '{mock_context.agent_id}' returned empty usage XML description." in caplog.text
    expected_error_tool_xml = '<tool_error name="EmptyXmlTool">Error: Usage information is empty for this tool.</tool_error>'
    expected_prompt = f"Tool: \n<tools>\n{expected_error_tool_xml}\n</tools>"
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_tool_returning_empty_json_logs_warning(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Tool: {{tools}}"
    tools: Dict[str, BaseTool] = {"EmptyJsonTool": mock_tool_alpha}
    
    mock_def = create_mock_definition("EmptyJsonTool", "", None) # Return None for empty JSON
    mock_registry.get_tool_definition.return_value = mock_def
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    assert f"Tool 'EmptyJsonTool' for agent '{mock_context.agent_id}' returned empty usage JSON description." in caplog.text
    expected_error_tool_json = json.dumps({"tool_error": {"name": "EmptyJsonTool", "message": "Error: Usage information is empty for this tool."}})
    expected_prompt = f"Tool: \n{expected_error_tool_json}"
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_tool_xml_generation_error_logs_error(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    prompt = "Tools: {{tools}}."
    tools = {"XmlErrorTool": mock_tool_alpha}
    
    mock_def = create_mock_definition("XmlErrorTool", None, None)
    mock_def.get_usage_xml.side_effect = RuntimeError("Simulated XML generation failure")
    mock_registry.get_tool_definition.return_value = mock_def

    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context) 
    
    expected_log_message_part = f"Failed to get usage XML for tool 'XmlErrorTool' for agent '{mock_context.agent_id}': Simulated XML generation failure"
    assert expected_log_message_part in caplog.text
    expected_error_tool_xml = '<tool_error name="XmlErrorTool">Error: Usage information could not be generated for this tool.</tool_error>'
    expected_prompt = f"Tools: \n<tools>\n{expected_error_tool_xml}\n</tools>."
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_tool_json_generation_error_logs_error(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    prompt = "Tools: {{tools}}."
    tools = {"JsonErrorTool": mock_tool_alpha}
    
    mock_def = create_mock_definition("JsonErrorTool", None, None)
    mock_def.get_usage_json.side_effect = RuntimeError("Simulated JSON generation failure")
    mock_registry.get_tool_definition.return_value = mock_def

    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)
    
    expected_log_message_part = f"Failed to get usage JSON for tool 'JsonErrorTool' for agent '{mock_context.agent_id}': Simulated JSON generation failure"
    assert expected_log_message_part in caplog.text
    expected_error_tool_json = json.dumps({"tool_error": {"name": "JsonErrorTool", "message": "Error: Usage information could not be generated for this tool."}})
    expected_prompt = f"Tools: \n{expected_error_tool_json}."
    assert processed_prompt == expected_prompt

def test_process_prompt_is_only_placeholder_with_no_tools(mock_context_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context_xml = mock_context_factory(use_xml=True, provider=LLMProvider.OPENAI)
    original_prompt = "{{tools}}"
    
    processed_prompt_xml = processor.process(original_prompt, {}, mock_context_xml.agent_id, mock_context_xml)
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    assert "Prepending default instructions." in caplog.text
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    expected_tools_part = "No tools available for this agent."
    assert processed_prompt_xml == expected_prefix + expected_tools_part
    caplog.clear()

    mock_context_json = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    processed_prompt_json = processor.process(original_prompt, {}, mock_context_json.agent_id, mock_context_json)
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    assert "Prepending default instructions." in caplog.text
    assert processed_prompt_json == expected_prefix + expected_tools_part

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_prompt_is_only_placeholder_with_tools_xml(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "  {{tools}}  " 
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}

    alpha_xml = "<tool name='AlphaTool' />"
    mock_alpha_def = create_mock_definition("AlphaTool", alpha_xml, {})
    mock_registry.get_tool_definition.return_value = mock_alpha_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    assert "Prepending default instructions." in caplog.text 
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    assert processed_prompt == expected_prefix + f"<tools>\n{alpha_xml}\n</tools>"

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_prompt_is_only_placeholder_with_tools_json(mock_registry, mock_tool_alpha: BaseTool, mock_context_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "  {{tools}}  "
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    alpha_json_schema = {"name": "AlphaTool", "description": "Desc Alpha", "input_schema": {}}
    mock_alpha_def = create_mock_definition("AlphaTool", "", alpha_json_schema)
    mock_registry.get_tool_definition.return_value = mock_alpha_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    assert "Prepending default instructions." in caplog.text
    expected_json_str = json.dumps(alpha_json_schema, indent=2)
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    assert processed_prompt == expected_prefix + expected_json_str

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_placeholder_in_middle_of_prompt_xml(mock_registry, mock_tool_beta: BaseTool, mock_context_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=True, provider=LLMProvider.ANTHROPIC)
    original_prompt = "Before placeholder. {{tools}} After placeholder."
    tools: Dict[str, BaseTool] = {"BetaTool": mock_tool_beta}

    beta_xml = "<tool name='BetaTool' />"
    mock_beta_def = create_mock_definition("BetaTool", beta_xml, {})
    mock_registry.get_tool_definition.return_value = mock_beta_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    expected_prompt = f"Before placeholder. \n<tools>\n{beta_xml}\n</tools> After placeholder."
    assert processed_prompt == expected_prompt

@patch('autobyteus.agent.system_prompt_processor.tool_description_injector_processor.default_tool_registry')
def test_process_placeholder_in_middle_of_prompt_json(mock_registry, mock_tool_beta: BaseTool, mock_context_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_factory(use_xml=False, provider=LLMProvider.OPENAI)
    original_prompt = "Before placeholder. {{tools}} After placeholder."
    tools: Dict[str, BaseTool] = {"BetaTool": mock_tool_beta}

    beta_json_schema = {"name": "BetaTool", "description": "Desc Beta", "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}}}
    mock_beta_def = create_mock_definition("BetaTool", "", beta_json_schema)
    mock_registry.get_tool_definition.return_value = mock_beta_def

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    expected_json_str = json.dumps(beta_json_schema, indent=2)
    expected_prompt = f"Before placeholder. \n{expected_json_str} After placeholder."
    assert processed_prompt == expected_prompt
