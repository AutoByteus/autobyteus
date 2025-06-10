import pytest
import logging 
import json
from typing import Dict
from unittest.mock import MagicMock

from autobyteus.agent.system_prompt_processor.tool_description_injector_processor import ToolDescriptionInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
# MockTool and fixtures (mock_tool_alpha, etc.) are available from conftest.py
# mock_context_for_system_prompt_processors_factory is available from conftest.py

def test_tool_injector_get_name():
    """Test the get_name() method of ToolDescriptionInjectorProcessor."""
    processor = ToolDescriptionInjectorProcessor()
    assert processor.get_name() == "ToolDescriptionInjector"

def test_process_prompt_without_placeholder(mock_context_for_system_prompt_processors_factory):
    """Test processing when the system prompt does not contain the '{{tools}}' placeholder."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "This is a simple system prompt."
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt, "Prompt should remain unchanged if placeholder is missing."

def test_process_with_placeholder_and_no_tools_xml(mock_context_for_system_prompt_processors_factory, caplog):
    """Test processing for XML when '{{tools}}' is present but no tools are provided."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Available tools: {{tools}}"
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    expected_prompt = "Available tools: \nNo tools available for this agent."
    assert processed_prompt == expected_prompt

def test_process_with_placeholder_and_no_tools_json(mock_context_for_system_prompt_processors_factory, caplog):
    """Test processing for JSON when '{{tools}}' is present but no tools are provided."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Available tools: {{tools}}"
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    expected_prompt = "Available tools: \nNo tools available for this agent." # Message is format-agnostic
    assert processed_prompt == expected_prompt


def test_process_with_placeholder_and_one_tool_xml(mock_tool_alpha: BaseTool, mock_context_for_system_prompt_processors_factory):
    """Test processing with '{{tools}}' and one available tool, XML format."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Please use {{tools}} for this task."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    expected_prompt = f"Please use \n{alpha_xml} for this task."
    assert processed_prompt == expected_prompt

def test_process_with_placeholder_and_one_tool_json(mock_tool_alpha: BaseTool, mock_context_for_system_prompt_processors_factory):
    """Test processing with '{{tools}}' and one available tool, JSON format."""
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Please use {{tools}} for this task."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    alpha_json_schema = {"name": "AlphaTool", "description": "Desc for Alpha", "input_schema": {}}
    mock_tool_alpha.tool_usage_json = MagicMock(return_value=alpha_json_schema)

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    expected_json_str = json.dumps(alpha_json_schema, indent=2)
    expected_prompt = f"Please use \n{expected_json_str} for this task."
    assert processed_prompt == expected_prompt
    mock_tool_alpha.tool_usage_json.assert_called_once()


def test_process_with_placeholder_and_multiple_tools_xml(mock_tool_alpha: BaseTool, mock_tool_beta: BaseTool, mock_context_for_system_prompt_processors_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Consider these: {{tools}}."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": mock_tool_beta}
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    beta_xml = mock_tool_beta.tool_usage_xml()
    
    assert "{{tools}}" not in processed_prompt
    assert alpha_xml in processed_prompt
    assert beta_xml in processed_prompt
    processed_tools_part = processed_prompt.replace("Consider these: ", "", 1).replace(".", "", 1)
    assert processed_tools_part.startswith("\n")
    # Order isn't guaranteed for dict iteration
    assert (f"\n{alpha_xml}\n{beta_xml}" in processed_tools_part or
            f"\n{beta_xml}\n{alpha_xml}" in processed_tools_part)


def test_process_with_placeholder_and_multiple_tools_json(mock_tool_alpha: BaseTool, mock_tool_beta: BaseTool, mock_context_for_system_prompt_processors_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Consider these: {{tools}}."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": mock_tool_beta}

    alpha_json_schema = {"name": "AlphaTool", "description": "Desc Alpha", "input_schema": {}}
    beta_json_schema = {"name": "BetaTool", "description": "Desc Beta", "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}}}
    mock_tool_alpha.tool_usage_json = MagicMock(return_value=alpha_json_schema)
    mock_tool_beta.tool_usage_json = MagicMock(return_value=beta_json_schema)

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    alpha_json_str = json.dumps(alpha_json_schema, indent=2)
    beta_json_str = json.dumps(beta_json_schema, indent=2)
    
    assert "{{tools}}" not in processed_prompt
    assert alpha_json_str in processed_prompt
    assert beta_json_str in processed_prompt
    processed_tools_part = processed_prompt.replace("Consider these: ", "", 1).replace(".", "", 1)
    assert processed_tools_part.startswith("\n")
    assert (f"\n{alpha_json_str}\n{beta_json_str}" in processed_tools_part or
            f"\n{beta_json_str}\n{alpha_json_str}" in processed_tools_part)


def test_process_tool_returning_empty_xml_logs_warning(mock_tool_empty_xml: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Tool: {{tools}}"
    tools: Dict[str, BaseTool] = {"EmptyXmlTool": mock_tool_empty_xml}
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    assert f"Tool 'EmptyXmlTool' for agent '{mock_context.agent_id}' returned empty usage XML description." in caplog.text
    expected_error_tool_xml = '<tool_error name="EmptyXmlTool">Error: Usage information is empty for this tool.</tool_error>'
    expected_prompt = f"Tool: \n{expected_error_tool_xml}"
    assert processed_prompt == expected_prompt

def test_process_tool_returning_empty_json_logs_warning(mock_tool_empty_xml: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Tool: {{tools}}"
    tools: Dict[str, BaseTool] = {"EmptyJsonTool": mock_tool_empty_xml}
    
    mock_tool_empty_xml.tool_usage_json = MagicMock(return_value=None)
    
    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    assert f"Tool 'EmptyJsonTool' for agent '{mock_context.agent_id}' returned empty usage JSON description." in caplog.text
    expected_error_tool_json = json.dumps({"tool_error": {"name": "EmptyJsonTool", "message": "Error: Usage information is empty for this tool."}})
    expected_prompt = f"Tool: \n{expected_error_tool_json}"
    assert processed_prompt == expected_prompt


def test_process_tool_xml_generation_error_logs_error(mock_tool_xml_error: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    prompt = "Tools: {{tools}}."
    tools = {"XmlErrorTool": mock_tool_xml_error}
    
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context) 
    
    expected_log_message_part = f"Failed to get usage XML for tool 'XmlErrorTool' for agent '{mock_context.agent_id}': Simulated XML generation failure"
    assert expected_log_message_part in caplog.text
    expected_error_tool_xml = '<tool_error name="XmlErrorTool">Error: Usage information could not be generated for this tool.</tool_error>'
    expected_prompt = f"Tools: \n{expected_error_tool_xml}."
    assert processed_prompt == expected_prompt

def test_process_tool_json_generation_error_logs_error(mock_tool_json_error: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    prompt = "Tools: {{tools}}."
    tools = {"JsonErrorTool": mock_tool_json_error}
    
    processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)
    
    expected_log_message_part = f"Failed to get usage JSON for tool 'JsonErrorTool' for agent '{mock_context.agent_id}': Simulated JSON generation failure"
    assert expected_log_message_part in caplog.text
    expected_error_tool_json = json.dumps({"tool_error": {"name": "JsonErrorTool", "message": "Error: Usage information could not be generated for this tool."}})
    expected_prompt = f"Tools: \n{expected_error_tool_json}."
    assert processed_prompt == expected_prompt


def test_process_prompt_is_only_placeholder_with_no_tools(mock_context_for_system_prompt_processors_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context_xml = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "{{tools}}"
    
    processed_prompt_xml = processor.process(original_prompt, {}, mock_context_xml.agent_id, mock_context_xml)
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    assert "Prepending default instructions." in caplog.text
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    expected_tools_part = "No tools available for this agent."
    assert processed_prompt_xml == expected_prefix + expected_tools_part
    caplog.clear()

    mock_context_json = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    processed_prompt_json = processor.process(original_prompt, {}, mock_context_json.agent_id, mock_context_json)
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text
    assert "Prepending default instructions." in caplog.text
    assert processed_prompt_json == expected_prefix + expected_tools_part


def test_process_prompt_is_only_placeholder_with_tools_xml(mock_tool_alpha: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "  {{tools}}  " 
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    assert "Prepending default instructions." in caplog.text 
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    assert processed_prompt == expected_prefix + alpha_xml

def test_process_prompt_is_only_placeholder_with_tools_json(mock_tool_alpha: BaseTool, mock_context_for_system_prompt_processors_factory, caplog):
    caplog.set_level(logging.INFO)
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "  {{tools}}  "
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    alpha_json_schema = {"name": "AlphaTool", "description": "Desc Alpha", "input_schema": {}}
    mock_tool_alpha.tool_usage_json = MagicMock(return_value=alpha_json_schema)

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    assert "Prepending default instructions." in caplog.text
    expected_json_str = json.dumps(alpha_json_schema, indent=2)
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    assert processed_prompt == expected_prefix + expected_json_str


def test_process_placeholder_in_middle_of_prompt_xml(mock_tool_beta: BaseTool, mock_context_for_system_prompt_processors_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Before placeholder. {{tools}} After placeholder."
    tools: Dict[str, BaseTool] = {"BetaTool": mock_tool_beta}

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context) 
    
    beta_xml = mock_tool_beta.tool_usage_xml()
    expected_prompt = f"Before placeholder. \n{beta_xml} After placeholder."
    assert processed_prompt == expected_prompt

def test_process_placeholder_in_middle_of_prompt_json(mock_tool_beta: BaseTool, mock_context_for_system_prompt_processors_factory):
    processor = ToolDescriptionInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Before placeholder. {{tools}} After placeholder."
    tools: Dict[str, BaseTool] = {"BetaTool": mock_tool_beta}

    beta_json_schema = {"name": "BetaTool", "description": "Desc Beta", "input_schema": {"type": "object", "properties": {"param1": {"type": "string"}}}}
    mock_tool_beta.tool_usage_json = MagicMock(return_value=beta_json_schema)

    processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)
    
    expected_json_str = json.dumps(beta_json_schema, indent=2)
    expected_prompt = f"Before placeholder. \n{expected_json_str} After placeholder."
    assert processed_prompt == expected_prompt
