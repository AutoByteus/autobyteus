# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_json_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.default_json_example_formatter import DefaultJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool

@pytest.fixture
def formatter():
    return DefaultJsonExampleFormatter()

@pytest.fixture
def complex_tool_def():
    """A complex tool definition for robust example testing."""
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

def test_provide_default_json_example_for_complex_tool(formatter: DefaultJsonExampleFormatter, complex_tool_def: ToolDefinition):
    json_output = formatter.provide(complex_tool_def)
    
    assert "tool" in json_output
    tool_call = json_output["tool"]
    
    assert tool_call["function"] == "ComplexTool"
    
    expected_params = {
        "input_path": "example_input_path",
        "retries": 3
    }
    assert tool_call["parameters"] == expected_params
