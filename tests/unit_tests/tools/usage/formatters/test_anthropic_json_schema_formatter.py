# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_anthropic_json_schema_formatter.py
import pytest

from autobyteus.tools.usage.formatters.anthropic_json_schema_formatter import AnthropicJsonSchemaFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return AnthropicJsonSchemaFormatter()

@pytest.fixture
def complex_tool_def():
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="The path to the input file.", required=True))
    schema.add_parameter(ParameterDefinition(name="overwrite", param_type=ParameterType.BOOLEAN, description="Overwrite existing file.", required=False, default_value=False))
    
    class DummyComplexTool(BaseTool):
        @classmethod
        def get_name(cls): return "AdvancedFileProcessor"
        @classmethod
        def get_description(cls): return "Processes a file with advanced options."
        @classmethod
        def get_argument_schema(cls): return schema
        async def _execute(self, **kwargs): pass

    return ToolDefinition(
        name="AdvancedFileProcessor",
        description="Processes a file with advanced options.",
        argument_schema=schema,
        tool_class=DummyComplexTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

def test_provide_anthropic_json_format(formatter: AnthropicJsonSchemaFormatter, complex_tool_def: ToolDefinition):
    json_output = formatter.provide(complex_tool_def)

    assert json_output["name"] == "AdvancedFileProcessor"
    assert json_output["description"] == "Processes a file with advanced options."
    
    input_schema = json_output["input_schema"]
    assert "input_path" in input_schema["properties"]
    assert "overwrite" in input_schema["properties"]
    assert "input_path" in input_schema["required"]
