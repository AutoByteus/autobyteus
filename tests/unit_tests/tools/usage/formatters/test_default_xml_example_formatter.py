# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_xml_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.default_xml_example_formatter import DefaultXmlExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool

@pytest.fixture
def formatter():
    return DefaultXmlExampleFormatter()

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

def test_provide_xml_example_for_complex_tool(formatter: DefaultXmlExampleFormatter, complex_tool_def: ToolDefinition):
    xml_output = formatter.provide(complex_tool_def)
    
    assert '<tool_call name="ComplexTool">' in xml_output
    assert '<arguments>' in xml_output
    assert '<arg name="input_path">example_input_path</arg>' in xml_output
    assert '<arg name="retries">3</arg>' in xml_output
    assert '<arg name="output_path">' not in xml_output
    assert '</arguments>' in xml_output
    assert '</tool_call>' in xml_output
