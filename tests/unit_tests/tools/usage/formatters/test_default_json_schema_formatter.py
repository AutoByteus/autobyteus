# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_json_schema_formatter.py
import pytest

from autobyteus.tools.usage.formatters.default_json_schema_formatter import DefaultJsonSchemaFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return DefaultJsonSchemaFormatter()

@pytest.fixture
def complex_tool_def():
    """
    A more complex tool definition that includes primitives, a nested object,
    an array of primitives, and an array of objects.
    """
    # Schema for a nested object (e.g., metadata)
    metadata_schema = ParameterSchema()
    metadata_schema.add_parameter(ParameterDefinition(name="author", param_type=ParameterType.STRING, description="The author of the file."))
    metadata_schema.add_parameter(ParameterDefinition(name="version", param_type=ParameterType.FLOAT, description="The file version.", required=True))

    # Schema for objects that will go in an array (e.g., revision history)
    revision_schema = ParameterSchema()
    revision_schema.add_parameter(ParameterDefinition(name="revision_id", param_type=ParameterType.INTEGER, description="The revision number."))
    revision_schema.add_parameter(ParameterDefinition(name="comment", param_type=ParameterType.STRING, description="A comment for the revision.", required=True))

    # Main schema for the tool
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="The path to the input file.", required=True))
    main_schema.add_parameter(ParameterDefinition(name="overwrite", param_type=ParameterType.BOOLEAN, description="Overwrite existing file.", required=False, default_value=False))
    main_schema.add_parameter(ParameterDefinition(name="tags", param_type=ParameterType.ARRAY, description="An array of primitive string tags.", required=False, array_item_schema=ParameterType.STRING))
    main_schema.add_parameter(ParameterDefinition(name="metadata", param_type=ParameterType.OBJECT, description="A nested object with file metadata.", required=False, object_schema=metadata_schema))
    main_schema.add_parameter(ParameterDefinition(name="revisions", param_type=ParameterType.ARRAY, description="An array of objects representing revisions.", required=False, array_item_schema=revision_schema))

    return ToolDefinition(
        name="AdvancedFileProcessor",
        description="Processes a file with advanced options.",
        argument_schema=main_schema,
        tool_class=BaseTool, # A dummy class is sufficient
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

def test_provide_default_json_format_for_complex_tool(formatter: DefaultJsonSchemaFormatter, complex_tool_def: ToolDefinition):
    """
    Tests that the formatter correctly generates a JSON schema for a tool with complex nested structures.
    """
    json_output = formatter.provide(complex_tool_def)

    # --- Top-Level Assertions ---
    assert json_output["name"] == "AdvancedFileProcessor"
    assert json_output["description"] == "Processes a file with advanced options."
    
    input_schema = json_output["inputSchema"]
    assert input_schema["type"] == "object"
    assert "input_path" in input_schema["required"]
    assert len(input_schema["required"]) == 1
    
    properties = input_schema["properties"]
    assert len(properties) == 5

    # --- Primitive Assertions ---
    assert properties["input_path"]["type"] == "string"
    assert properties["overwrite"]["type"] == "boolean"
    assert properties["overwrite"]["default"] is False

    # --- Array of Primitives Assertion ---
    tags_schema = properties["tags"]
    assert tags_schema["type"] == "array"
    assert tags_schema["items"]["type"] == "string"
    assert tags_schema["description"] == "An array of primitive string tags."

    # --- Nested Object Assertion ---
    metadata_schema_json = properties["metadata"]
    assert metadata_schema_json["type"] == "object"
    assert metadata_schema_json["description"] == "A nested object with file metadata."
    assert "author" in metadata_schema_json["properties"]
    assert "version" in metadata_schema_json["properties"]
    assert metadata_schema_json["properties"]["author"]["type"] == "string"
    assert metadata_schema_json["properties"]["version"]["type"] == "number" # FLOAT maps to number
    assert "version" in metadata_schema_json["required"]
    assert len(metadata_schema_json["required"]) == 1

    # --- Array of Objects Assertion ---
    revisions_schema = properties["revisions"]
    assert revisions_schema["type"] == "array"
    assert revisions_schema["description"] == "An array of objects representing revisions."
    
    revision_item_schema = revisions_schema["items"]
    assert revision_item_schema["type"] == "object"
    assert "revision_id" in revision_item_schema["properties"]
    assert "comment" in revision_item_schema["properties"]
    assert revision_item_schema["properties"]["revision_id"]["type"] == "integer"
    assert revision_item_schema["properties"]["comment"]["type"] == "string"
    assert "comment" in revision_item_schema["required"]
    assert len(revision_item_schema["required"]) == 1
