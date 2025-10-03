# file: autobyteus/tests/unit_tests/tools/mcp/test_schema_mapper.py
import pytest
from autobyteus.tools.mcp.schema_mapper import McpSchemaMapper
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

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

def test_map_array_of_primitives(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "description": "List of tags", "items": {"type": "string"}},
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    
    tags_param = param_schema.get_parameter("tags")
    assert tags_param is not None
    assert tags_param.param_type == ParameterType.ARRAY
    assert tags_param.array_item_schema == {"type": "string"}

def test_map_nested_object_recursively(schema_mapper: McpSchemaMapper):
    mcp_schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "description": "User details",
                "properties": {
                    "name": {"type": "string", "description": "User's name"}
                },
                "required": ["name"]
            }
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    user_param = param_schema.get_parameter("user")
    
    assert user_param is not None
    assert user_param.param_type == ParameterType.OBJECT
    assert isinstance(user_param.object_schema, ParameterSchema)
    
    nested_schema = user_param.object_schema
    assert len(nested_schema.parameters) == 1
    nested_name_param = nested_schema.get_parameter("name")
    assert nested_name_param is not None
    assert nested_name_param.param_type == ParameterType.STRING
    assert nested_name_param.required is True

def test_map_deeply_nested_object_schema(schema_mapper: McpSchemaMapper):
    """Tests that the mapper can handle more than one level of recursion."""
    mcp_schema = {
        "type": "object",
        "properties": {
            "level1": {
                "type": "object",
                "description": "First level",
                "properties": {
                    "level2": {
                        "type": "object",
                        "description": "Second level",
                        "properties": {
                            "name": {"type": "string", "description": "Deepest name"}
                        }
                    }
                }
            }
        }
    }
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_schema)
    level1_param = param_schema.get_parameter("level1")
    assert isinstance(level1_param.object_schema, ParameterSchema)
    
    level2_param = level1_param.object_schema.get_parameter("level2")
    assert isinstance(level2_param.object_schema, ParameterSchema)
    
    name_param = level2_param.object_schema.get_parameter("name")
    assert name_param.param_type == ParameterType.STRING
    assert name_param.description == "Deepest name"

def test_map_unsupported_root_type_raises_error(schema_mapper: McpSchemaMapper):
    """Verifies that the new stricter mapper rejects non-object root schemas."""
    mcp_schema_string_root = {"type": "string", "description": "Root is string"}
    with pytest.raises(ValueError, match="MCP JSON schema root 'type' must be 'object'"):
        schema_mapper.map_to_autobyteus_schema(mcp_schema_string_root)
    
    mcp_schema_invalid_root = {"type": "custom_unknown", "description": "Unknown type"}
    with pytest.raises(ValueError, match="MCP JSON schema root 'type' must be 'object'"):
        schema_mapper.map_to_autobyteus_schema(mcp_schema_invalid_root)

# --- Parametrized Test with Real-World Nested Data ---

def _validate_schema_recursively(param_schema: ParameterSchema, expected_details: list, tool_name: str, path: str):
    """Recursive helper to validate nested schemas."""
    assert len(param_schema.parameters) == len(expected_details), \
        f"{path}: Number of mapped parameters mismatch. Expected {len(expected_details)}, got {len(param_schema.parameters)}."

    for expected in expected_details:
        param_name = expected["name"]
        current_path = f"{path}.{param_name}"
        actual = param_schema.get_parameter(param_name)

        assert actual is not None, f"{current_path}: Expected parameter not found."
        assert actual.param_type == expected["type"], f"{current_path}: Type mismatch."
        assert actual.description == expected.get("description", f"Parameter '{param_name}'."), f"{current_path}: Description mismatch."
        assert actual.required == expected.get("required", False), f"{current_path}: Required status mismatch."
        
        if "nested_schema" in expected:
            assert isinstance(actual.object_schema, ParameterSchema), f"{current_path}: Expected a nested ParameterSchema."
            _validate_schema_recursively(actual.object_schema, expected["nested_schema"], tool_name, current_path)

REAL_MCP_SCHEMAS_DATA = [
    (
        "batch_update_presentation",
        {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "The ID of the presentation to update."},
                "requests": {
                    "type": "array",
                    "description": "A list of update requests.",
                    "items": {"type": "object"}
                },
                "writeControl": {
                    "type": "object",
                    "description": "Control over write requests.",
                    "properties": {
                        "requiredRevisionId": {"type": "string", "description": "Required revision ID."},
                        "targetRevisionId": {"type": "string", "description": "Target revision ID."}
                    }
                }
            },
            "required": ["presentationId", "requests"]
        },
        [
            {"name": "presentationId", "type": ParameterType.STRING, "description": "The ID of the presentation to update.", "required": True},
            {"name": "requests", "type": ParameterType.ARRAY, "description": "A list of update requests.", "required": True},
            {
                "name": "writeControl",
                "type": ParameterType.OBJECT,
                "description": "Control over write requests.",
                "required": False,
                "nested_schema": [
                    {"name": "requiredRevisionId", "type": ParameterType.STRING, "description": "Required revision ID.", "required": False},
                    {"name": "targetRevisionId", "type": ParameterType.STRING, "description": "Target revision ID.", "required": False}
                ]
            }
        ]
    )
]

@pytest.mark.parametrize("tool_name, mcp_input_schema, expected_params_details", REAL_MCP_SCHEMAS_DATA)
def test_map_real_nested_mcp_schema(
    schema_mapper: McpSchemaMapper, 
    tool_name: str, 
    mcp_input_schema: dict, 
    expected_params_details: list
):
    param_schema = schema_mapper.map_to_autobyteus_schema(mcp_input_schema)
    _validate_schema_recursively(param_schema, expected_params_details, tool_name, tool_name)
