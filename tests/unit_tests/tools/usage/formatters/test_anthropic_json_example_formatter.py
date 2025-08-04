# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_anthropic_json_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.anthropic_json_example_formatter import AnthropicJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return AnthropicJsonExampleFormatter()

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

def test_provide_anthropic_example(formatter: AnthropicJsonExampleFormatter, complex_tool_def: ToolDefinition):
    xml_output = formatter.provide(complex_tool_def)
    
    assert isinstance(xml_output, str)
    # Anthropic uses XML, which is handled by the DefaultXmlExampleFormatter
    assert '<tool name="ComplexTool">' in xml_output
    assert '<arg name="input_path">example_input_path</arg>' in xml_output
    assert '<arg name="retries">3</arg>' in xml_output
