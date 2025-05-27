# file: autobyteus/tests/unit_tests/tools/mcp/test_schema_mapper.py
import pytest
from autobyteus.tools.mcp.schema_mapper import McpSchemaMapper
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

@pytest.fixture
def schema_mapper() -> McpSchemaMapper:
    return McpSchemaMapper()

def test_map_basic_object_schema(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "User name"},
            "age": {"type": "integer", "description": "User age", "default": 30},
            "is_member": {"type": "boolean", "description": "Membership status"}
        },
        "required": ["name"]
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    
    assert len(param_schema.parameters) == 3
    
    name_param = param_schema.get_parameter("name")
    assert name_param is not None
    assert name_param.param_type == ParameterType.STRING
    assert name_param.description == "User name"
    assert name_param.required is True

    age_param = param_schema.get_parameter("age")
    assert age_param is not None
    assert age_param.param_type == ParameterType.INTEGER
    assert age_param.default_value == 30
    assert age_param.required is False

    member_param = param_schema.get_parameter("is_member")
    assert member_param is not None
    assert member_param.param_type == ParameterType.BOOLEAN
    assert member_param.required is False

def test_map_path_heuristics(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "input_file_path": {"type": "string", "description": "Input file"},
            "output_folder": {"type": "string", "description": "Output directory"}
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    
    file_param = param_schema.get_parameter("input_file_path")
    assert file_param is not None
    assert file_param.param_type == ParameterType.FILE_PATH

    dir_param = param_schema.get_parameter("output_folder")
    assert dir_param is not None
    assert dir_param.param_type == ParameterType.DIRECTORY_PATH

def test_map_enum_type(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "color": {"type": "string", "description": "Color choice", "enum": ["red", "green", "blue"]}
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    color_param = param_schema.get_parameter("color")
    assert color_param is not None
    assert color_param.param_type == ParameterType.ENUM
    assert color_param.enum_values == ["red", "green", "blue"]

def test_map_array_type(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "description": "List of tags", "items": {"type": "string"}},
            "scores": {"type": "array", "description": "List of scores", "items": {"type": "integer"}},
            "generic_list": {"type": "array", "description": "Untyped list"} # items defaults to true
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    
    tags_param = param_schema.get_parameter("tags")
    assert tags_param is not None
    assert tags_param.param_type == ParameterType.ARRAY
    assert tags_param.array_item_schema == {"type": "string"}

    scores_param = param_schema.get_parameter("scores")
    assert scores_param is not None
    assert scores_param.param_type == ParameterType.ARRAY
    assert scores_param.array_item_schema == {"type": "integer"}

    generic_param = param_schema.get_parameter("generic_list")
    assert generic_param is not None
    assert generic_param.param_type == ParameterType.ARRAY
    assert generic_param.array_item_schema is True # Default when items is not specified or unmappable

def test_map_object_type(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "metadata": {"type": "object", "description": "Some metadata"}
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    meta_param = param_schema.get_parameter("metadata")
    assert meta_param is not None
    assert meta_param.param_type == ParameterType.OBJECT

def test_map_unsupported_root_type(schema_mapper: McpSchemaMapper):
    mcp_schema_string_root = {"type": "string", "description": "Root is string"}
    # Current behavior might try to create a single "input_value" param
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema_string_root)
    assert len(param_schema.parameters) == 1
    input_val_param = param_schema.get_parameter("input_value")
    assert input_val_param is not None
    assert input_val_param.param_type == ParameterType.STRING
    
    mcp_schema_invalid_root = {"type": "custom_unknown", "description": "Unknown type"}
    with pytest.raises(ValueError, match="MCP JSON schema root 'type' must be 'object' for typical mapping"):
        schema_mapper.map_to_autobyteus_schema(mcp_schema_invalid_root)

def test_map_empty_properties(schema_mapper: McpSchemaMapper):
    mcp_schema = {"type": "object", "properties": {}}
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    assert len(param_schema.parameters) == 0

    mcp_schema_no_props = {"type": "object"} # No properties field
    param_schema_no_props = schema_mapper.map_to_autobyteus_schema(mcp_schema_no_props)
    assert len(param_schema_no_props.parameters) == 0

def test_map_invalid_schema_input(schema_mapper: McpSchemaMapper):
    with pytest.raises(ValueError, match="MCP JSON schema must be a dictionary"):
        schema_mapper.map_to_autobyteus_schema("not a dict") # type: ignore

