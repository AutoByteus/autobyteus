# file: autobyteus/tests/unit_tests/agent/system_prompt_processor/test_tool_usage_example_injector_processor.py
from unittest.mock import patch, MagicMock # Added MagicMock
import pytest
import logging
import json 
from typing import Dict, Optional, Any

from autobyteus.agent.system_prompt_processor.tool_usage_example_injector_processor import ToolUsageExampleInjectorProcessor
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

from ._test_helpers import MockTool 
# mock_context_for_system_prompt_processors_factory is available from conftest.py


def test_tool_example_injector_get_name():
    assert ToolUsageExampleInjectorProcessor.get_name() == "ToolUsageExampleInjector"

def test_process_prompt_without_placeholder(mock_context_for_system_prompt_processors_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory()
    original_prompt = "This is a system prompt without the examples placeholder."
    # The context argument was missing in the original call, process now requires it.
    processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    assert processed_prompt == original_prompt

def test_process_with_placeholder_and_no_tools(mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory()
    original_prompt = "Tool examples: {{tool_examples}}"
    
    with caplog.at_level(logging.INFO):
        processed_prompt = processor.process(original_prompt, {}, mock_context.agent_id, mock_context)
    
    assert f"{processor.get_name()}: No tools available for agent '{mock_context.agent_id}'." in caplog.text
    expected_prompt = f"Tool examples: {processor.DEFAULT_NO_TOOLS_MESSAGE}"
    assert processed_prompt == expected_prompt

# Test for XML examples (use_xml_tool_format = True)
def test_process_with_one_tool_no_args_xml_format(mock_context_for_system_prompt_processors_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    original_prompt = "Example: {{tool_examples}}"
    
    tool_no_args_instance = MockTool(name="NoArgsTool", description="Tool with no args")
    tools: Dict[str, BaseTool] = {"NoArgsTool": tool_no_args_instance}

    with patch.object(tool_no_args_instance, 'get_name', return_value="NoArgsTool"), \
         patch.object(tool_no_args_instance, 'get_argument_schema', return_value=ParameterSchema()):
        processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    expected_xml_example = (
        f'<command name="NoArgsTool">\n'
        f'    <!-- This tool takes no arguments. -->\n'
        f'</command>'
    )
    
    assert processor.XML_EXAMPLES_HEADER in processed_prompt
    assert expected_xml_example in processed_prompt
    assert processor.JSON_EXAMPLES_HEADER not in processed_prompt # Ensure JSON header is NOT present
    assert "{{tool_examples}}" not in processed_prompt
    assert "json.dumps" not in str(processor._generate_tool_example_json_obj) # Check internal calls if needed or trust logic

# Test for JSON examples (use_xml_tool_format = False)
def test_process_with_one_tool_no_args_json_format(mock_context_for_system_prompt_processors_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    original_prompt = "Example: {{tool_examples}}"
    
    tool_no_args_instance = MockTool(name="NoArgsTool", description="Tool with no args")
    tools: Dict[str, BaseTool] = {"NoArgsTool": tool_no_args_instance}

    with patch.object(tool_no_args_instance, 'get_name', return_value="NoArgsTool"), \
         patch.object(tool_no_args_instance, 'get_argument_schema', return_value=ParameterSchema()):
        processed_prompt = processor.process(original_prompt, tools, mock_context.agent_id, mock_context)

    expected_json_example_obj = {"tool_name": "NoArgsTool", "arguments": {}}
    expected_json_example_str = json.dumps(expected_json_example_obj, indent=2) # Indent 2 for JSON

    assert processor.JSON_EXAMPLES_HEADER in processed_prompt
    assert expected_json_example_str in processed_prompt
    assert processor.XML_EXAMPLES_HEADER not in processed_prompt # Ensure XML header is NOT present
    assert "{{tool_examples}}" not in processed_prompt


def test_process_with_tool_having_required_and_defaulted_args_xml_format(mock_context_for_system_prompt_processors_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    prompt = "Examples: {{tool_examples}}"
    
    test_schema = ParameterSchema()
    test_schema.add_parameter(ParameterDefinition(name="path", param_type=ParameterType.FILE_PATH, description="File path", required=True))
    test_schema.add_parameter(ParameterDefinition(name="count", param_type=ParameterType.INTEGER, description="A number", required=False, default_value=10))
    test_schema.add_parameter(ParameterDefinition(name="active", param_type=ParameterType.BOOLEAN, description="Is active", required=True))
    
    tool_mix_args_instance = MockTool(name="MixArgsTool", description="Tool with mixed args")
    tools: Dict[str, BaseTool] = {"MixArgsTool": tool_mix_args_instance}

    with patch.object(tool_mix_args_instance, 'get_name', return_value="MixArgsTool"), \
         patch.object(tool_mix_args_instance, 'get_argument_schema', return_value=test_schema):
        processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)
    
    expected_xml_example = (
        f'<command name="MixArgsTool">\n'
        f'    <arg name="path">/path/to/your/file.txt</arg>\n'
        f'    <arg name="count">10</arg>\n'
        f'    <arg name="active">true</arg>\n'
        f'</command>'
    )
    
    assert processor.XML_EXAMPLES_HEADER in processed_prompt
    assert expected_xml_example in processed_prompt
    assert processor.JSON_EXAMPLES_HEADER not in processed_prompt

def test_process_with_tool_having_required_and_defaulted_args_json_format(mock_context_for_system_prompt_processors_factory):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    prompt = "Examples: {{tool_examples}}"
    
    test_schema = ParameterSchema()
    test_schema.add_parameter(ParameterDefinition(name="path", param_type=ParameterType.FILE_PATH, description="File path", required=True))
    test_schema.add_parameter(ParameterDefinition(name="count", param_type=ParameterType.INTEGER, description="A number", required=False, default_value=10))
    test_schema.add_parameter(ParameterDefinition(name="active", param_type=ParameterType.BOOLEAN, description="Is active", required=True))
    
    tool_mix_args_instance = MockTool(name="MixArgsTool", description="Tool with mixed args")
    tools: Dict[str, BaseTool] = {"MixArgsTool": tool_mix_args_instance}

    with patch.object(tool_mix_args_instance, 'get_name', return_value="MixArgsTool"), \
         patch.object(tool_mix_args_instance, 'get_argument_schema', return_value=test_schema):
        processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)
    
    expected_json_example_obj = {
        "tool_name": "MixArgsTool",
        "arguments": {
            "path": "/path/to/your/file.txt",
            "count": 10,
            "active": True
        }
    }
    expected_json_example_str = json.dumps(expected_json_example_obj, indent=2)
    
    assert processor.JSON_EXAMPLES_HEADER in processed_prompt
    assert expected_json_example_str in processed_prompt
    assert processor.XML_EXAMPLES_HEADER not in processed_prompt

# Parameterize placeholder generation test as it's format-agnostic for py_val
@pytest.mark.parametrize("param_type, expected_placeholder_val_py, expected_placeholder_val_xml_str", [
    (ParameterType.STRING, "example_string_value", "example_string_value"),
    (ParameterType.INTEGER, 123, "123"),
    (ParameterType.FLOAT, 123.45, "123.45"),
    (ParameterType.BOOLEAN, True, "true"), 
    (ParameterType.ENUM, "option1", "option1"), 
    (ParameterType.FILE_PATH, "/path/to/your/file.txt", "/path/to/your/file.txt"),
    (ParameterType.DIRECTORY_PATH, "/path/to/your/directory/", "/path/to/your/directory/"),
    (ParameterType.OBJECT, {"key1": "example_value", "key2": 100}, "{'key1': 'example_value', 'key2': 100}"), 
    (ParameterType.ARRAY, ["example_item1", 2, True], "['example_item1', 2, True]"), 
])
def test_generate_placeholder_value_and_xml_string_conversion(param_type: ParameterType, expected_placeholder_val_py: Any, expected_placeholder_val_xml_str: str):
    processor = ToolUsageExampleInjectorProcessor()
    param_def_args: Dict[str, Any] = {"name": "test_param", "param_type": param_type, "description": "Test"}
    if param_type == ParameterType.ENUM:
        param_def_args["enum_values"] = ["option1", "option2"]
    
    param_def = ParameterDefinition(**param_def_args)
    
    py_val = processor._generate_placeholder_value(param_def)
    assert py_val == expected_placeholder_val_py

    # Test XML string conversion part specifically
    xml_str_val = str(py_val)
    if isinstance(py_val, bool): 
        xml_str_val = 'true' if py_val else 'false'
    assert xml_str_val == expected_placeholder_val_xml_str


def test_generate_placeholder_value_name_heuristics():
    processor = ToolUsageExampleInjectorProcessor()
    def_query = ParameterDefinition(name="searchQuery", param_type=ParameterType.STRING, description="q")
    assert processor._generate_placeholder_value(def_query) == "example search query"
    def_url = ParameterDefinition(name="pageUrl", param_type=ParameterType.STRING, description="url")
    assert processor._generate_placeholder_value(def_url) == "https://example.com"


def test_process_failure_to_generate_example_for_one_tool_xml_format(mock_tool_alpha: MockTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=True)
    prompt = "Examples: {{tool_examples}}"

    alpha_schema = ParameterSchema() 
    alpha_schema.add_parameter(ParameterDefinition(name="alpha_param", param_type=ParameterType.STRING, description="Param for Alpha."))
    
    tool_beta_instance = MockTool(name="BetaTool", description="Beta desc")
    beta_schema = ParameterSchema()

    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": tool_beta_instance}

    with patch.object(processor, '_generate_tool_example_xml', autospec=True) as mock_gen_xml_proc_method, \
         patch.object(mock_tool_alpha, 'get_name', return_value="AlphaTool"), \
         patch.object(mock_tool_alpha, 'get_argument_schema', return_value=alpha_schema), \
         patch.object(tool_beta_instance, 'get_name', return_value="BetaTool"), \
         patch.object(tool_beta_instance, 'get_argument_schema', return_value=beta_schema):
        
        def side_effect_xml(tool_instance_param: BaseTool) -> str:
            instance_name = tool_instance_param.get_name() 
            if instance_name == "AlphaTool":
                raise RuntimeError("Simulated XML example failure for AlphaTool")
            return f"<command name=\"{instance_name}\"><!-- XML Example for {instance_name} --></command>"
        
        mock_gen_xml_proc_method.side_effect = side_effect_xml
        
        processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    assert "Failed to generate XML example for tool 'AlphaTool'" in caplog.text
    assert "<!-- Error generating XML example for tool: AlphaTool -->" in processed_prompt
    assert "<command name=\"BetaTool\"><!-- XML Example for BetaTool --></command>" in processed_prompt 
    assert "{{tool_examples}}" not in processed_prompt
    assert processor.JSON_EXAMPLES_HEADER not in processed_prompt # Check JSON specific things are not there

def test_process_failure_to_generate_example_for_one_tool_json_format(mock_tool_alpha: MockTool, mock_context_for_system_prompt_processors_factory, caplog):
    processor = ToolUsageExampleInjectorProcessor()
    mock_context = mock_context_for_system_prompt_processors_factory(use_xml_format=False)
    prompt = "Examples: {{tool_examples}}"

    alpha_schema = ParameterSchema()
    alpha_schema.add_parameter(ParameterDefinition(name="alpha_param", param_type=ParameterType.STRING, description="Param for Alpha."))
    
    tool_beta_instance = MockTool(name="BetaTool", description="Beta desc")
    beta_schema = ParameterSchema()

    tools: Dict[str, BaseTool] = {"AlphaTool": mock_tool_alpha, "BetaTool": tool_beta_instance}

    with patch.object(processor, '_generate_tool_example_json_obj', autospec=True) as mock_gen_json_proc_method, \
         patch.object(mock_tool_alpha, 'get_name', return_value="AlphaTool"), \
         patch.object(mock_tool_alpha, 'get_argument_schema', return_value=alpha_schema), \
         patch.object(tool_beta_instance, 'get_name', return_value="BetaTool"), \
         patch.object(tool_beta_instance, 'get_argument_schema', return_value=beta_schema):
        
        def side_effect_json(tool_instance_param: BaseTool) -> Dict[str, Any]:
            instance_name = tool_instance_param.get_name()
            if instance_name == "AlphaTool":
                raise RuntimeError("Simulated JSON example failure for AlphaTool")
            return {"tool_name": instance_name, "arguments": {"note": f"JSON Example for {instance_name}"}}

        mock_gen_json_proc_method.side_effect = side_effect_json
        
        processed_prompt = processor.process(prompt, tools, mock_context.agent_id, mock_context)

    assert "Failed to generate JSON example for tool 'AlphaTool'" in caplog.text
    assert "// Error generating JSON example for tool: AlphaTool" in processed_prompt
    
    beta_json_example_obj = {"tool_name": "BetaTool", "arguments": {"note": "JSON Example for BetaTool"}}
    beta_json_example_str = json.dumps(beta_json_example_obj, indent=2)
    assert beta_json_example_str in processed_prompt
    
    assert "{{tool_examples}}" not in processed_prompt
    assert processor.XML_EXAMPLES_HEADER not in processed_prompt # Check XML specific things are not there

