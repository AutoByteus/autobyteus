# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_gemini_json_schema_formatter.py
import pytest

from autobyteus.tools.usage.formatters.gemini_json_schema_formatter import GeminiJsonSchemaFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return GeminiJsonSchemaFormatter()

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
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: schema,
        config_schema_provider=lambda: None,
        tool_class=DummyComplexTool
    )

def test_provide_gemini_json_format(formatter: GeminiJsonSchemaFormatter, complex_tool_def: ToolDefinition):
    json_output = formatter.provide(complex_tool_def)

    assert json_output["name"] == "AdvancedFileProcessor"
    assert json_output["description"] == "Processes a file with advanced options."
    
    parameters = json_output["parameters"]
    assert "input_path" in parameters["properties"]
    assert "overwrite" in parameters["properties"]
    assert "input_path" in parameters["required"]
