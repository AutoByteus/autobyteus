# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_xml_schema_formatter.py
import pytest
import re
from pydantic import BaseModel, Field
from typing import List

from autobyteus.tools.usage.formatters.default_xml_schema_formatter import DefaultXmlSchemaFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

def normalize_xml(xml_string: str) -> str:
    """Helper to normalize whitespace for consistent comparison."""
    return "\n".join(line.strip() for line in xml_string.strip().split('\n') if line.strip())

@pytest.fixture
def formatter():
    return DefaultXmlSchemaFormatter()

# --- Pydantic Models for Converter Test ---
class PydanticItem(BaseModel):
    name: str = Field(description="The item name.")
    value: int = Field(description="The item value.")

class PydanticContainer(BaseModel):
    items: List[PydanticItem] = Field(description="A list of items.")

# --- Fixtures for Schemas ---

@pytest.fixture
def complex_tool_def():
    """A tool definition with various primitive argument types."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="The path to the input file.", required=True))
    schema.add_parameter(ParameterDefinition(name="mode", param_type=ParameterType.ENUM, description="Processing mode.", required=True, enum_values=["read", "write"]))
    schema.add_parameter(ParameterDefinition(name="overwrite", param_type=ParameterType.BOOLEAN, description="Overwrite existing file.", required=False, default_value=False))
    
    return ToolDefinition(
        name="AdvancedFileProcessor",
        description="Processes a file with advanced options.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

@pytest.fixture
def no_arg_tool_def():
    """A tool definition with no arguments."""
    return ToolDefinition(
        name="NoArgTool",
        description="A tool with no arguments.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

@pytest.fixture
def nested_object_schema() -> ParameterSchema:
    """A schema for a nested 'person' object."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="name", param_type=ParameterType.STRING, description="The name of the person.", required=True))
    schema.add_parameter(ParameterDefinition(name="age", param_type=ParameterType.INTEGER, description="The age of the person.", required=False))
    return schema

@pytest.fixture
def nested_object_tool_def(nested_object_schema: ParameterSchema) -> ToolDefinition:
    """A tool definition that takes a nested object."""
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="user_profile",
        param_type=ParameterType.OBJECT,
        description="The user's profile.",
        object_schema=nested_object_schema
    ))
    return ToolDefinition(
        name="UserProfileTool",
        description="A tool for user profiles.",
        origin=ToolOrigin.LOCAL,
        category="test",
        argument_schema_provider=lambda: main_schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

@pytest.fixture
def array_of_objects_tool_def(nested_object_schema: ParameterSchema) -> ToolDefinition:
    """A tool definition that takes an array of nested objects."""
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="users",
        param_type=ParameterType.ARRAY,
        description="A list of users.",
        array_item_schema=nested_object_schema
    ))
    return ToolDefinition(
        name="UserListTool",
        description="A tool for user lists.",
        origin=ToolOrigin.LOCAL,
        category="test",
        argument_schema_provider=lambda: main_schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

@pytest.fixture
def array_of_objects_dict_schema_tool_def() -> ToolDefinition:
    """A tool definition that takes an array of objects defined with a raw dict schema."""
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="users",
        param_type=ParameterType.ARRAY,
        description="A list of users.",
        array_item_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the person."},
                "age": {"type": "integer", "description": "The age of the person."}
            },
            "required": ["name"]
        }
    ))
    return ToolDefinition(
        name="UserListTool",
        description="A tool for user lists.",
        origin=ToolOrigin.LOCAL,
        category="test",
        argument_schema_provider=lambda: main_schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )


@pytest.fixture
def array_of_strings_tool_def() -> ToolDefinition:
    """A tool definition that takes an array of strings."""
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="tags",
        param_type=ParameterType.ARRAY,
        description="A list of tags.",
        array_item_schema=ParameterType.STRING
    ))
    return ToolDefinition(
        name="TaggerTool",
        description="A tool for tagging.",
        origin=ToolOrigin.LOCAL,
        category="test",
        argument_schema_provider=lambda: main_schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )


# --- TESTS ---

def test_provide_with_complex_flat_schema(formatter: DefaultXmlSchemaFormatter, complex_tool_def: ToolDefinition):
    xml_output = formatter.provide(complex_tool_def)
    
    expected_xml = """
    <tool name="AdvancedFileProcessor" description="Processes a file with advanced options.">
        <arguments>
            <arg name="input_path" type="string" description="The path to the input file." required="true" />
            <arg name="mode" type="enum" description="Processing mode." required="true" enum_values="read,write" />
            <arg name="overwrite" type="boolean" description="Overwrite existing file." required="false" default="False" />
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_no_args(formatter: DefaultXmlSchemaFormatter, no_arg_tool_def: ToolDefinition):
    xml_output = formatter.provide(no_arg_tool_def)
    
    expected_xml = """
    <tool name="NoArgTool" description="A tool with no arguments.">
        <!-- This tool takes no arguments -->
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_nested_object(formatter: DefaultXmlSchemaFormatter, nested_object_tool_def: ToolDefinition):
    xml_output = formatter.provide(nested_object_tool_def)
    
    expected_xml = """
    <tool name="UserProfileTool" description="A tool for user profiles.">
        <arguments>
            <arg name="user_profile" type="object" description="The user's profile." required="false">
                <arg name="name" type="string" description="The name of the person." required="true" />
                <arg name="age" type="integer" description="The age of the person." required="false" />
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_array_of_objects(formatter: DefaultXmlSchemaFormatter, array_of_objects_tool_def: ToolDefinition):
    xml_output = formatter.provide(array_of_objects_tool_def)

    expected_xml = """
    <tool name="UserListTool" description="A tool for user lists.">
        <arguments>
            <arg name="users" type="array" description="A list of users." required="false">
                <items type="object">
                    <arg name="name" type="string" description="The name of the person." required="true" />
                    <arg name="age" type="integer" description="The age of the person." required="false" />
                </items>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_array_of_objects_dict_schema(formatter: DefaultXmlSchemaFormatter, array_of_objects_dict_schema_tool_def: ToolDefinition):
    """This test specifically validates the bug fix for array item schemas that are dicts."""
    xml_output = formatter.provide(array_of_objects_dict_schema_tool_def)

    expected_xml = """
    <tool name="UserListTool" description="A tool for user lists.">
        <arguments>
            <arg name="users" type="array" description="A list of users." required="false">
                <items type="object">
                    <arg name="name" type="string" description="The name of the person." required="true" />
                    <arg name="age" type="integer" description="The age of the person." required="false" />
                </items>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_array_of_strings(formatter: DefaultXmlSchemaFormatter, array_of_strings_tool_def: ToolDefinition):
    xml_output = formatter.provide(array_of_strings_tool_def)

    expected_xml = """
    <tool name="TaggerTool" description="A tool for tagging.">
        <arguments>
            <arg name="tags" type="array" description="A list of tags." required="false">
                <items type="string" />
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)

def test_provide_with_schema_from_pydantic_converter(formatter: DefaultXmlSchemaFormatter):
    """
    This is an end-to-end test that verifies the formatter works correctly with
    a schema generated by the pydantic_to_parameter_schema converter, specifically
    for an array of objects.
    """
    # 1. Generate the schema using the converter
    generated_schema = pydantic_to_parameter_schema(PydanticContainer)
    
    # 2. Create a ToolDefinition with this generated schema
    tool_def = ToolDefinition(
        name="PydanticContainerTool",
        description="A tool for Pydantic containers.",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=lambda: generated_schema,
        config_schema_provider=lambda: None,
        custom_factory=lambda: None
    )

    # 3. Format the schema to XML
    xml_output = formatter.provide(tool_def)

    # 4. Assert the output is correct and complete
    expected_xml = """
    <tool name="PydanticContainerTool" description="A tool for Pydantic containers.">
        <arguments>
            <arg name="items" type="array" description="A list of items." required="true">
                <items type="object">
                    <arg name="name" type="string" description="The item name." required="true" />
                    <arg name="value" type="integer" description="The item value." required="true" />
                </items>
            </arg>
        </arguments>
    </tool>
    """
    assert normalize_xml(xml_output) == normalize_xml(expected_xml)
