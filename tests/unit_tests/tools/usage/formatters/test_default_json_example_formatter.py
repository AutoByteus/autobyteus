# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_json_example_formatter.py
import pytest
import json
import re

from autobyteus.tools.usage.formatters.default_json_example_formatter import DefaultJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

def extract_json_from_block(block_text: str):
    """Helper to extract and parse JSON from a markdown code block."""
    match = re.search(r"```json\s*([\s\S]+?)\s*```", block_text)
    if not match:
        raise ValueError("Could not find JSON code block in text")
    return json.loads(match.group(1))

@pytest.fixture
def formatter():
    return DefaultJsonExampleFormatter()

# --- Fixtures ---

@pytest.fixture
def simple_tool_def():
    """A tool with only required parameters."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    
    return ToolDefinition(
        name="SimpleTool",
        description="A simple tool.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

@pytest.fixture
def complex_tool_def():
    """A tool with required, optional, and default-value parameters."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    schema.add_parameter(ParameterDefinition(name="retries", param_type=ParameterType.INTEGER, description="Number of retries.", required=False, default_value=3))
    
    return ToolDefinition(
        name="ComplexTool",
        description="A complex tool.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

# --- Test Cases ---

def test_simple_tool_provides_single_example(formatter: DefaultJsonExampleFormatter, simple_tool_def: ToolDefinition):
    """Tests that a tool with only required args produces a single example string."""
    output = formatter.provide(simple_tool_def)
    
    assert isinstance(output, str)
    assert "### Example 1: Basic Call (Required Arguments)" in output
    assert "### Example 2:" not in output
    
    parsed_json = extract_json_from_block(output)
    assert parsed_json["tool"]["function"] == "SimpleTool"
    assert parsed_json["tool"]["parameters"] == {"input_path": "example_input_path"}

def test_complex_tool_provides_multiple_examples(formatter: DefaultJsonExampleFormatter, complex_tool_def: ToolDefinition):
    """Tests that a tool with optional args produces a string with two examples."""
    output = formatter.provide(complex_tool_def)

    assert isinstance(output, str)
    parts = output.split('\n\n')
    assert len(parts) == 2
    
    basic_block, advanced_block = parts
    
    assert "### Example 1: Basic Call (Required Arguments)" in basic_block
    assert "### Example 2: Advanced Call (With Optional Arguments)" in advanced_block

    # Test basic call
    basic_json = extract_json_from_block(basic_block)
    assert basic_json["tool"]["function"] == "ComplexTool"
    assert basic_json["tool"]["parameters"] == {"input_path": "example_input_path"}

    # Test advanced call
    advanced_json = extract_json_from_block(advanced_block)
    assert advanced_json["tool"]["function"] == "ComplexTool"
    assert advanced_json["tool"]["parameters"] == {"input_path": "example_input_path", "retries": 3}
