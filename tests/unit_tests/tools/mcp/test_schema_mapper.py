# file: autobyteus/tests/unit_tests/mcp/test_schema_mapper.py
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

def test_map_path_heuristics_now_string(schema_mapper: McpSchemaMapper): # RENAMED and logic changed
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
    # Now expecting STRING instead of FILE_PATH
    assert file_param.param_type == ParameterType.STRING 
    assert "Input file" in file_param.description # Description should remain

    dir_param = param_schema.get_parameter("output_folder")
    assert dir_param is not None
    # Now expecting STRING instead of DIRECTORY_PATH
    assert dir_param.param_type == ParameterType.STRING 
    assert "Output directory" in dir_param.description # Description should remain


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
            "generic_list": {"type": "array", "description": "Untyped list"} 
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
    assert generic_param.array_item_schema is True 

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

    mcp_schema_no_props = {"type": "object"} 
    param_schema_no_props = schema_mapper.map_to_autobyteus_schema(mcp_schema_no_props)
    assert len(param_schema_no_props.parameters) == 0

def test_map_invalid_schema_input(schema_mapper: McpSchemaMapper):
    with pytest.raises(ValueError, match="MCP JSON schema must be a dictionary"):
        schema_mapper.map_to_autobyteus_schema("not a dict") # type: ignore


REAL_MCP_SCHEMAS_DATA = [
    (
        "create_presentation", 
        {
            "type": "object",
            "properties": {"title": {"type": "string", "description": "The title of the presentation."}},
            "required": ["title"]
        },
        [
            {"name": "title", "type": ParameterType.STRING, "description": "The title of the presentation.", "required": True}
        ]
    ),
    (
        "get_presentation",
        {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "The ID of the presentation to retrieve."},
                "fields": {"type": "string", "description": "Optional. A mask specifying which fields to include in the response (e.g., \"slides,pageSize\")."}
            },
            "required": ["presentationId"]
        },
        [
            {"name": "presentationId", "type": ParameterType.STRING, "description": "The ID of the presentation to retrieve.", "required": True},
            {"name": "fields", "type": ParameterType.STRING, "description": "Optional. A mask specifying which fields to include in the response (e.g., \"slides,pageSize\").", "required": False}
        ]
    ),
    (
        "batch_update_presentation",
        {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "The ID of the presentation to update."},
                "requests": {
                    "type": "array",
                    "description": "A list of update requests to apply. See Google Slides API documentation for request structures.",
                    "items": {"type": "object"}
                },
                "writeControl": {
                    "type": "object",
                    "description": "Optional. Provides control over how write requests are executed.",
                    "properties": {
                        "requiredRevisionId": {"type": "string"},
                        "targetRevisionId": {"type": "string"}
                    }
                }
            },
            "required": ["presentationId", "requests"]
        },
        [
            {"name": "presentationId", "type": ParameterType.STRING, "description": "The ID of the presentation to update.", "required": True},
            {"name": "requests", "type": ParameterType.ARRAY, "description": "A list of update requests to apply. See Google Slides API documentation for request structures.", "required": True, "array_item_schema": {"type": "object"}},
            {"name": "writeControl", "type": ParameterType.OBJECT, "description": "Optional. Provides control over how write requests are executed.", "required": False}
        ]
    ),
    (
        "get_page",
        {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "The ID of the presentation."},
                "pageObjectId": {"type": "string", "description": "The object ID of the page (slide) to retrieve."}
            },
            "required": ["presentationId", "pageObjectId"]
        },
        [
            {"name": "presentationId", "type": ParameterType.STRING, "description": "The ID of the presentation.", "required": True},
            {"name": "pageObjectId", "type": ParameterType.STRING, "description": "The object ID of the page (slide) to retrieve.", "required": True}
        ]
    ),
    (
        "summarize_presentation",
        {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "The ID of the presentation to summarize."},
                "include_notes": {"type": "boolean", "description": "Optional. Whether to include speaker notes in the summary (default: false)."}
            },
            "required": ["presentationId"]
        },
        [
            {"name": "presentationId", "type": ParameterType.STRING, "description": "The ID of the presentation to summarize.", "required": True},
            {"name": "include_notes", "type": ParameterType.BOOLEAN, "description": "Optional. Whether to include speaker notes in the summary (default: false).", "required": False}
        ]
    )
]

@pytest.mark.parametrize("tool_name, mcp_input_schema, expected_params_details", REAL_MCP_SCHEMAS_DATA)
def test_map_real_google_slides_mcp_schemas(
    schema_mapper: McpSchemaMapper, 
    tool_name: str, 
    mcp_input_schema: dict, 
    expected_params_details: list
):
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_input_schema)

    assert len(param_schema.parameters) == len(expected_params_details), \
        f"Tool '{tool_name}': Number of mapped parameters mismatch. Expected {len(expected_params_details)}, got {len(param_schema.parameters)}."

    for expected_detail in expected_params_details:
        param_name = expected_detail["name"]
        actual_param_def = param_schema.get_parameter(param_name)

        assert actual_param_def is not None, \
            f"Tool '{tool_name}': Expected parameter '{param_name}' not found in mapped schema."
        
        assert actual_param_def.name == param_name, \
             f"Tool '{tool_name}', Param '{param_name}': Name mismatch."
        assert actual_param_def.param_type == expected_detail["type"], \
            f"Tool '{tool_name}', Param '{param_name}': Type mismatch. Expected {expected_detail['type']}, got {actual_param_def.param_type}."
        assert actual_param_def.description == expected_detail["description"], \
            f"Tool '{tool_name}', Param '{param_name}': Description mismatch."
        assert actual_param_def.required == expected_detail["required"], \
            f"Tool '{tool_name}', Param '{param_name}': Required status mismatch."
        
        if "array_item_schema" in expected_detail:
            assert actual_param_def.array_item_schema == expected_detail["array_item_schema"], \
                f"Tool '{tool_name}', Param '{param_name}': array_item_schema mismatch."
        else:
            assert actual_param_def.array_item_schema is None, \
                f"Tool '{tool_name}', Param '{param_name}': Expected no array_item_schema, but found one."
        if "default_value" in expected_detail: 
            assert actual_param_def.default_value == expected_detail["default_value"], \
                f"Tool '{tool_name}', Param '{param_name}': Default value mismatch."
