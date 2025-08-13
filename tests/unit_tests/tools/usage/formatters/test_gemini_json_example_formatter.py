# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_gemini_json_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.gemini_json_example_formatter import GeminiJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return GeminiJsonExampleFormatter()

@pytest.fixture
def complex_tool_def():
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
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
        tool_class=DummyComplexTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

def test_provide_gemini_json_example(formatter: GeminiJsonExampleFormatter, complex_tool_def: ToolDefinition):
    json_output = formatter.provide(complex_tool_def)
    
    assert json_output["name"] == "ComplexTool"
    assert json_output["args"] == {
        "input_path": "example_input_path",
        "retries": 3
    }
