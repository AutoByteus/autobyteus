# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_openai_json_example_formatter.py
import pytest
import json

from autobyteus.tools.usage.formatters.openai_json_example_formatter import OpenAiJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool

@pytest.fixture
def formatter():
    return OpenAiJsonExampleFormatter()

@pytest.fixture
def complex_tool_def():
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    schema.add_parameter(ParameterDefinition(name="output_path", param_type=ParameterType.STRING, description="Output path.", required=False))
    schema.add_parameter(ParameterDefinition(name="retries", param_type=ParameterType.INTEGER, description="Number of retries.", required=False, default_value=3))
    
    class DummyComplexTool(BaseTool):
        @classmethod
        def get_name(cls): return "ComplexTool"
        @classmethod
        def get_description(cls): return "A complex tool."
        @classmethod
        def get_argument_schema(cls): return schema
        async def _execute(self, **kwargs): pass
        
    return ToolDefinition(
        name="ComplexTool",
        description="A complex tool.",
        argument_schema=schema,
        tool_class=DummyComplexTool
    )

def test_provide_openai_json_example_for_complex_tool(formatter: OpenAiJsonExampleFormatter, complex_tool_def: ToolDefinition):
    """
    Tests that the formatter produces the format with the 'function' wrapper.
    """
    json_output = formatter.provide(complex_tool_def)
    
    assert "name" not in json_output
    assert "function" in json_output
    
    function_part = json_output["function"]
    assert function_part["name"] == "ComplexTool"
    
    # Assert arguments is a JSON string
    assert isinstance(function_part["arguments"], str)
    arguments = json.loads(function_part["arguments"])
    
    expected_args = {
        "input_path": "example_input_path",
        "retries": 3
    }
    assert arguments == expected_args
