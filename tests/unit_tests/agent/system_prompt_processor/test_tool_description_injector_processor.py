import pytest
import logging # Import logging
from typing import Dict

from autobyteus.agent.system_prompt_processor.tool_description_injector_processor import ToolDescriptionInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
# MockTool and fixtures (mock_tool_alpha, etc.) are available from conftest.py

def test_tool_injector_get_name():
    """Test the get_name() method of ToolDescriptionInjectorProcessor."""
    assert ToolDescriptionInjectorProcessor.get_name() == "ToolDescriptionInjector"

def test_process_prompt_without_placeholder():
    """Test processing when the system prompt does not contain the '{{tools}}' placeholder."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "This is a simple system prompt."
    processed_prompt = processor.process(original_prompt, {}, "agent_x")
    assert processed_prompt == original_prompt, "Prompt should remain unchanged if placeholder is missing."

def test_process_with_placeholder_and_no_tools(caplog):
    """Test processing when '{{tools}}' is present but no tools are provided."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "Available tools: {{tools}}"
    processed_prompt = processor.process(original_prompt, {}, "agent_y")
    
    # Check log message (this is a WARNING level, should be captured by default)
    assert "Replacing with 'No tools available.'" in caplog.text
    # Check prompt modification
    expected_prompt = "Available tools: \nNo tools available for this agent."
    assert processed_prompt == expected_prompt

def test_process_with_placeholder_and_one_tool(mock_tool_alpha: BaseTool):
    """Test processing with '{{tools}}' and one available tool."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "Please use {{tools}} for this task."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}
    
    processed_prompt = processor.process(original_prompt, tools, "agent_z") # type: ignore
    
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    expected_prompt = f"Please use \n{alpha_xml} for this task."
    assert processed_prompt == expected_prompt

def test_process_with_placeholder_and_multiple_tools(mock_tool_alpha: BaseTool, mock_tool_beta: BaseTool):
    """Test processing with '{{tools}}' and multiple available tools."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "Consider these: {{tools}}."
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": mock_tool_beta}
    
    processed_prompt = processor.process(original_prompt, tools, "agent_multi") # type: ignore
    
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    beta_xml = mock_tool_beta.tool_usage_xml()
    
    assert "{{tools}}" not in processed_prompt
    assert alpha_xml in processed_prompt
    assert beta_xml in processed_prompt
    
    expected_structure_part = f"\n{alpha_xml}\n{beta_xml}"
    alternative_expected_structure_part = f"\n{beta_xml}\n{alpha_xml}"
    # Check that the processed part starts with a newline and contains both XMLs
    processed_tools_part = processed_prompt.replace("Consider these: ", "", 1)
    assert processed_tools_part.startswith("\n")
    assert (expected_structure_part in processed_tools_part or
            alternative_expected_structure_part in processed_tools_part)


def test_process_tool_returning_empty_xml_logs_warning(mock_tool_empty_xml: BaseTool, caplog):
    """Test processing when a tool returns an empty string for its XML."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "Tool: {{tools}}"
    tools: Dict[str, BaseTool] = {"EmptyXmlTool": mock_tool_empty_xml}
    
    processed_prompt = processor.process(original_prompt, tools, "agent_empty_tool") # type: ignore
    
    assert "Tool 'EmptyXmlTool' for agent 'agent_empty_tool' returned empty usage XML." in caplog.text
    expected_error_tool_xml = '<tool_error name="EmptyXmlTool">Error: Usage information is empty for this tool.</tool_error>'
    expected_prompt = f"Tool: \n{expected_error_tool_xml}"
    assert processed_prompt == expected_prompt

def test_process_tool_xml_generation_error_logs_error(mock_tool_xml_error: BaseTool, caplog):
    """Test when tool_usage_xml raises an error."""
    processor = ToolDescriptionInjectorProcessor()
    prompt = "Tools: {{tools}}."
    tools = {"XmlErrorTool": mock_tool_xml_error}
    
    processed_prompt = processor.process(prompt, tools, "agent1") # type: ignore
    
    expected_log_message_part = "Failed to get usage XML for tool 'XmlErrorTool' for agent 'agent1': Simulated XML generation failure"
    assert expected_log_message_part in caplog.text
    
    expected_error_tool_xml = '<tool_error name="XmlErrorTool">Error: Usage information could not be generated for this tool.</tool_error>'
    expected_prompt = f"Tools: \n{expected_error_tool_xml}."
    assert processed_prompt == expected_prompt


def test_process_prompt_is_only_placeholder_with_no_tools(caplog):
    """Test when prompt is exclusively '{{tools}}' and no tools are available."""
    # Ensure INFO logs are captured for this test
    caplog.set_level(logging.INFO, logger="autobyteus.agent.system_prompt_processor.tool_description_injector_processor")
    
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "{{tools}}" # Exactly the placeholder
    
    processed_prompt = processor.process(original_prompt, {}, "agent_solo_placeholder_no_tools")
    
    # Both the WARNING (no tools) and INFO (prepending) logs should be present
    assert "no tools are instantiated. Replacing with 'No tools available.'" in caplog.text # WARNING
    assert "Prepending default instructions." in caplog.text # INFO
    
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    expected_tools_part = "No tools available for this agent."
    assert processed_prompt == expected_prefix + expected_tools_part

def test_process_prompt_is_only_placeholder_with_tools(mock_tool_alpha: BaseTool, caplog):
    """Test when prompt is exclusively '{{tools}}' (with whitespace) and tools are available."""
    # Ensure INFO logs are captured for this test
    caplog.set_level(logging.INFO, logger="autobyteus.agent.system_prompt_processor.tool_description_injector_processor")

    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "  {{tools}}  " # Placeholder with surrounding whitespace
    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha}

    processed_prompt = processor.process(original_prompt, tools, "agent_solo_placeholder_with_tools") # type: ignore
    
    assert "Prepending default instructions." in caplog.text # INFO log
    alpha_xml = mock_tool_alpha.tool_usage_xml()
    expected_prefix = ToolDescriptionInjectorProcessor.DEFAULT_PREFIX_FOR_TOOLS_ONLY_PROMPT
    assert processed_prompt == expected_prefix + alpha_xml

def test_process_placeholder_in_middle_of_prompt(mock_tool_beta: BaseTool):
    """Test when '{{tools}}' is surrounded by other text in the prompt."""
    processor = ToolDescriptionInjectorProcessor()
    original_prompt = "Before placeholder. {{tools}} After placeholder."
    tools: Dict[str, BaseTool] = {"BetaTool": mock_tool_beta}

    processed_prompt = processor.process(original_prompt, tools, "agent_middle_placeholder") # type: ignore
    
    beta_xml = mock_tool_beta.tool_usage_xml()
    expected_prompt = f"Before placeholder. \n{beta_xml} After placeholder."
    assert processed_prompt == expected_prompt

