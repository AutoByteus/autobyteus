import pytest
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

@pytest.fixture
def nested_object_schema() -> ParameterSchema:
    """Provides a schema for a nested object (e.g., a 'person')."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(
        name="name",
        param_type=ParameterType.STRING,
        description="The name of the person.",
        required=True
    ))
    schema.add_parameter(ParameterDefinition(
        name="age",
        param_type=ParameterType.INTEGER,
        description="The age of the person.",
        required=False
    ))
    return schema

def test_define_nested_object(nested_object_schema: ParameterSchema):
    """
    Tests defining a parameter that is an object with its own schema.
    """
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="user_profile",
        param_type=ParameterType.OBJECT,
        description="The user's profile information.",
        object_schema=nested_object_schema
    ))

    param = main_schema.get_parameter("user_profile")
    assert param is not None
    assert param.param_type == ParameterType.OBJECT
    assert isinstance(param.object_schema, ParameterSchema)
    assert len(param.object_schema.parameters) == 2
    assert param.object_schema.get_parameter("name").required is True

def test_to_json_schema_for_nested_object(nested_object_schema: ParameterSchema):
    """
    Verifies that to_json_schema_dict correctly generates a nested JSON schema for objects.
    """
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="user_profile",
        param_type=ParameterType.OBJECT,
        description="The user's profile.",
        required=True,
        object_schema=nested_object_schema
    ))

    json_schema = main_schema.to_json_schema_dict()
    
    expected = {
        "type": "object",
        "properties": {
            "user_profile": {
                "type": "object",
                "description": "The user's profile.",
                "properties": {
                    "name": {"type": "string", "description": "The name of the person."},
                    "age": {"type": "integer", "description": "The age of the person."}
                },
                "required": ["name"]
            }
        },
        "required": ["user_profile"]
    }
    assert json_schema == expected

def test_to_json_schema_for_array_of_objects_dict_schema():
    """
    Verifies that to_json_schema_dict correctly generates a nested JSON schema for an array of objects
    when the item schema is a dictionary.
    """
    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(
        name="users",
        param_type=ParameterType.ARRAY,
        description="A list of user profiles.",
        array_item_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the person."},
                "age": {"type": "integer", "description": "The age of the person."}
            },
            "required": ["name"]
        }
    ))

    json_schema = main_schema.to_json_schema_dict()

    expected = {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "description": "A list of user profiles.",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the person."},
                        "age": {"type": "integer", "description": "The age of the person."}
                    },
                    "required": ["name"]
                }
            }
        },
        "required": []
    }
    assert json_schema == expected

def test_serialization_deserialization_nested(nested_object_schema: ParameterSchema):
    """
    Ensures that a schema with nested objects can be serialized to a dict and deserialized back.
    """
    original_schema = ParameterSchema()
    original_schema.add_parameter(ParameterDefinition(
        name="user_profile",
        param_type=ParameterType.OBJECT,
        description="A user profile.",
        object_schema=nested_object_schema
    ))
    
    # Serialize to dict
    schema_dict = original_schema.to_dict()
    
    # Deserialize back to object
    deserialized_schema = ParameterSchema.from_dict(schema_dict)

    assert len(deserialized_schema.parameters) == 1
    param = deserialized_schema.get_parameter("user_profile")
    assert param is not None
    assert param.param_type == ParameterType.OBJECT
    
    obj_schema = param.object_schema
    assert isinstance(obj_schema, ParameterSchema)
    assert len(obj_schema.parameters) == 2
    assert obj_schema.get_parameter("name").description == "The name of the person."

def test_validation_rejects_wrong_type():
    """
    Tests that __post_init__ validation rejects incorrect types for nested schemas.
    """
    with pytest.raises(ValueError, match="object_schema must be a ParameterSchema instance"):
        ParameterDefinition(
            name="profile",
            param_type=ParameterType.OBJECT,
            description="A profile.",
            object_schema={"key": "value"} # This is a dict, not a ParameterSchema
        )
