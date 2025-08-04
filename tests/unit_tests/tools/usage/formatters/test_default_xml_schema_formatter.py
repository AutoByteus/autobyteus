# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_xml_schema_formatter.py
import pytest
import re

from autobyteus.tools.usage.formatters.default_xml_schema_formatter import DefaultXmlSchemaFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return DefaultXmlSchemaFormatter()

@pytest.fixture
def complex_tool_def():
    """A more complex tool definition for robust testing."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="The path to the input file.", required=True))
    schema.add_parameter(ParameterDefinition(name="output_path", param_type=ParameterType.STRING, description="Optional path for the output file.", required=False))
    schema.add_parameter(ParameterDefinition(name="mode", param_type=ParameterType.ENUM, description="Processing mode.", required=True, enum_values=["read", "write"]))
    schema.add_parameter(ParameterDefinition(name="overwrite", param_type=ParameterType.BOOLEAN, description="Overwrite existing file.", required=False, default_value=False))
    schema.add_parameter(ParameterDefinition(name="retries", param_type=ParameterType.INTEGER, description="Number of retries.", required=False, default_value=3))
    
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

@pytest.fixture
def no_arg_tool_def():
    class DummyNoArgTool(BaseTool):
        @classmethod
        def get_name(cls): return "NoArgTool"
        @classmethod
        def get_description(cls): return "A tool with no arguments."
        @classmethod
        def get_argument_schema(cls): return None
        async def _execute(self, **kwargs): pass

    return ToolDefinition(
        name="NoArgTool",
        description="A tool with no arguments.",
        argument_schema=None,
        tool_class=DummyNoArgTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

def test_provide_with_complex_schema(formatter: DefaultXmlSchemaFormatter, complex_tool_def: ToolDefinition):
    xml_output = formatter.provide(complex_tool_def)
    
    assert '<tool name="AdvancedFileProcessor" description="Processes a file with advanced options.">' in xml_output
    assert '<arguments>' in xml_output # Check for the new arguments wrapper
    
    # Check that args are inside the arguments block
    assert re.search(r'<arguments>.*<arg\s+name="input_path"', xml_output, re.DOTALL)
    
    # Check for specific argument definitions
    assert re.search(r'<arg\s+name="input_path"\s+type="string"\s+description="The path to the input file."\s+required="true"\s*/>', xml_output)
    assert re.search(r'<arg\s+name="mode"\s+type="enum"\s+description="Processing mode."\s+required="true"\s+enum_values="read,write"\s*/>', xml_output)
    assert re.search(r'<arg\s+name="overwrite"\s+type="boolean"\s+description="Overwrite existing file."\s+required="false"\s+default="False"\s*/>', xml_output)
    
    assert '</arguments>' in xml_output
    assert '</tool>' in xml_output

def test_provide_with_no_args(formatter: DefaultXmlSchemaFormatter, no_arg_tool_def: ToolDefinition):
    xml_output = formatter.provide(no_arg_tool_def)
    assert '<tool name="NoArgTool" description="A tool with no arguments.">' in xml_output
    assert "<!-- This tool takes no arguments -->" in xml_output
    assert "<arguments>" not in xml_output
