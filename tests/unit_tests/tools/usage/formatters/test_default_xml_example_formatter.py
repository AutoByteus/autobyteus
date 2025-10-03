# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_xml_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.default_xml_example_formatter import DefaultXmlExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

def normalize_xml(xml_string: str) -> str:
    """Helper to normalize whitespace for consistent comparison."""
    return "\n".join(line.strip() for line in xml_string.strip().split('\n') if line.strip())

@pytest.fixture
def formatter():
    return DefaultXmlExampleFormatter()

# --- Fixtures ---

@pytest.fixture
def simple_tool_def():
    """A tool with only required parameters."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    schema.add_parameter(ParameterDefinition(name="output_path", param_type=ParameterType.STRING, description="Output path.", required=True))
    
    return ToolDefinition(
        name="SimpleCopyTool",
        description="A simple tool.",
        argument_schema=schema,
        custom_factory=lambda: None,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

@pytest.fixture
def complex_tool_def():
    """A tool with required, optional, and default-value parameters."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    schema.add_parameter(ParameterDefinition(name="output_path", param_type=ParameterType.STRING, description="Optional output path.", required=False))
    schema.add_parameter(ParameterDefinition(name="retries", param_type=ParameterType.INTEGER, description="Number of retries.", required=False, default_value=3))
    
    return ToolDefinition(
        name="ComplexTool",
        description="A complex tool.",
        argument_schema=schema,
        custom_factory=lambda: None,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

@pytest.fixture
def nested_object_tool_def() -> ToolDefinition:
    nested_schema = ParameterSchema()
    nested_schema.add_parameter(ParameterDefinition(name="street", param_type=ParameterType.STRING, description="Street.", required=True))
    nested_schema.add_parameter(ParameterDefinition(name="city", param_type=ParameterType.STRING, description="City.", required=True))
    nested_schema.add_parameter(ParameterDefinition(name="zip", param_type=ParameterType.STRING, description="Zip code.", required=False))

    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(name="address", param_type=ParameterType.OBJECT, description="An address.", required=True, object_schema=nested_schema))
    
    return ToolDefinition("AddressTool", "A tool for addresses.", main_schema, ToolOrigin.LOCAL, "test", custom_factory=lambda: None)

@pytest.fixture
def array_of_strings_tool_def() -> ToolDefinition:
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(name="filename", param_type=ParameterType.STRING, description="Filename.", required=True))
    main_schema.add_parameter(ParameterDefinition(
        name="tags",
        param_type=ParameterType.ARRAY,
        description="An optional list of tags.",
        required=False,
        array_item_schema=ParameterType.STRING
    ))
    return ToolDefinition("TaggerTool", "A tool for tagging.", main_schema, ToolOrigin.LOCAL, "test", custom_factory=lambda: None)

# --- Tests ---

def test_simple_tool_only_generates_basic_example(formatter: DefaultXmlExampleFormatter, simple_tool_def: ToolDefinition):
    """A tool with only required params should not generate an advanced example."""
    output = formatter.provide(simple_tool_def)
    
    assert "### Example 1: Basic Call (Required Arguments)" in output
    assert "### Example 2: Advanced Call" not in output

    expected_basic_xml = """
    <tool name="SimpleCopyTool">
        <arguments>
            <arg name="input_path">A valid string for 'input_path'</arg>
            <arg name="output_path">A valid string for 'output_path'</arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_basic_xml) in normalize_xml(output)

def test_complex_tool_generates_basic_and_advanced_examples(formatter: DefaultXmlExampleFormatter, complex_tool_def: ToolDefinition):
    """A tool with optional/default params should generate two examples."""
    output = formatter.provide(complex_tool_def)
    
    assert "### Example 1: Basic Call (Required Arguments)" in output
    assert "### Example 2: Advanced Call (With Optional & Nested Arguments)" in output
    
    # Check Example 1 (basic)
    expected_basic_xml = """
    <tool name="ComplexTool">
        <arguments>
            <arg name="input_path">A valid string for 'input_path'</arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_basic_xml) in normalize_xml(output)

    # Check Example 2 (advanced)
    expected_advanced_xml = """
    <tool name="ComplexTool">
        <arguments>
            <arg name="input_path">A valid string for 'input_path'</arg>
            <arg name="output_path">A valid string for 'output_path'</arg>
            <arg name="retries">3</arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_advanced_xml) in normalize_xml(output)

def test_nested_object_tool_generates_correct_examples(formatter: DefaultXmlExampleFormatter, nested_object_tool_def: ToolDefinition):
    output = formatter.provide(nested_object_tool_def)
    
    assert "### Example 1: Basic Call (Required Arguments)" in output
    assert "### Example 2: Advanced Call (With Optional & Nested Arguments)" in output

    # Check Example 1 (basic) - includes the object but only its required fields
    expected_basic_xml = """
    <tool name="AddressTool">
        <arguments>
            <arg name="address">
                <arg name="street">A valid string for 'street'</arg>
                <arg name="city">A valid string for 'city'</arg>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_basic_xml) in normalize_xml(output)

    # Check Example 2 (advanced) - should now include the optional 'zip' field
    expected_advanced_xml = """
    <tool name="AddressTool">
        <arguments>
            <arg name="address">
                <arg name="street">A valid string for 'street'</arg>
                <arg name="city">A valid string for 'city'</arg>
                <arg name="zip">A valid string for 'zip'</arg>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_advanced_xml) in normalize_xml(output)

def test_array_tool_shows_array_in_advanced_example(formatter: DefaultXmlExampleFormatter, array_of_strings_tool_def: ToolDefinition):
    output = formatter.provide(array_of_strings_tool_def)
    
    assert "### Example 1: Basic Call (Required Arguments)" in output
    assert "### Example 2: Advanced Call (With Optional & Nested Arguments)" in output

    # Check Example 1 (basic) - should only have 'filename'
    expected_basic_xml = """
    <tool name="TaggerTool">
        <arguments>
            <arg name="filename">A valid string for 'filename'</arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_basic_xml) in normalize_xml(output)
    
    # Check Example 2 (advanced) - should have 'filename' AND the optional 'tags' array
    expected_advanced_xml = """
    <tool name="TaggerTool">
        <arguments>
            <arg name="filename">A valid string for 'filename'</arg>
            <arg name="tags">
                <item>A valid string for 'tags_item_1'</item>
                <item>A valid string for 'tags_item_2'</item>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(expected_advanced_xml) in normalize_xml(output)
