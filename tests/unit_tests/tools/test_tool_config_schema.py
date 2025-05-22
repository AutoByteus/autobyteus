# File: tests/unit_tests/tools/test_tool_config_schema.py
import pytest
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType

def test_parameter_type_enum():
    assert ParameterType.STRING == "string"
    assert ParameterType.INTEGER == "integer"
    assert ParameterType.BOOLEAN == "boolean"

def test_tool_config_parameter_creation():
    param = ToolConfigParameter(
        name="test_param",
        param_type=ParameterType.STRING,
        description="A test parameter"
    )
    
    assert param.name == "test_param"
    assert param.param_type == ParameterType.STRING
    assert param.description == "A test parameter"
    assert not param.required
    assert param.default_value is None

def test_tool_config_parameter_invalid_name():
    with pytest.raises(ValueError, match="Parameter name must be a non-empty string"):
        ToolConfigParameter(
            name="",
            param_type=ParameterType.STRING,
            description="Test"
        )

def test_tool_config_parameter_invalid_description():
    with pytest.raises(ValueError, match="must have a non-empty description"):
        ToolConfigParameter(
            name="test",
            param_type=ParameterType.STRING,
            description=""
        )

def test_tool_config_parameter_enum_without_values():
    with pytest.raises(ValueError, match="must specify enum_values"):
        ToolConfigParameter(
            name="test",
            param_type=ParameterType.ENUM,
            description="Test enum"
        )

def test_tool_config_parameter_validate_string():
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test string"
    )
    
    assert param.validate_value("valid_string")
    assert not param.validate_value(123)
    assert param.validate_value(None)  # Not required

def test_tool_config_parameter_validate_integer():
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.INTEGER,
        description="Test integer",
        min_value=1,
        max_value=100
    )
    
    assert param.validate_value(50)
    assert not param.validate_value(0)  # Below min
    assert not param.validate_value(101)  # Above max
    assert not param.validate_value("50")  # Wrong type

def test_tool_config_parameter_validate_enum():
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.ENUM,
        description="Test enum",
        enum_values=["option1", "option2", "option3"]
    )
    
    assert param.validate_value("option1")
    assert param.validate_value("option2")
    assert not param.validate_value("invalid_option")
    assert not param.validate_value(1)

def test_tool_config_parameter_to_dict():
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test parameter",
        required=True,
        default_value="default"
    )
    
    result = param.to_dict()
    expected = {
        "name": "test",
        "type": "string",
        "description": "Test parameter",
        "required": True,
        "default_value": "default",
        "enum_values": None,
        "min_value": None,
        "max_value": None,
        "pattern": None,
    }
    
    assert result == expected

def test_tool_config_schema_creation():
    schema = ToolConfigSchema()
    assert len(schema) == 0
    assert not schema

def test_tool_config_schema_add_parameter():
    schema = ToolConfigSchema()
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test parameter"
    )
    
    schema.add_parameter(param)
    assert len(schema) == 1
    assert schema

def test_tool_config_schema_add_duplicate_parameter():
    schema = ToolConfigSchema()
    param1 = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test parameter 1"
    )
    param2 = ToolConfigParameter(
        name="test",
        param_type=ParameterType.INTEGER,
        description="Test parameter 2"
    )
    
    schema.add_parameter(param1)
    
    with pytest.raises(ValueError, match="already exists in schema"):
        schema.add_parameter(param2)

def test_tool_config_schema_get_parameter():
    schema = ToolConfigSchema()
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test parameter"
    )
    
    schema.add_parameter(param)
    
    retrieved = schema.get_parameter("test")
    assert retrieved is param
    assert schema.get_parameter("nonexistent") is None

def test_tool_config_schema_validate_config():
    schema = ToolConfigSchema()
    
    required_param = ToolConfigParameter(
        name="required_param",
        param_type=ParameterType.STRING,
        description="Required parameter",
        required=True
    )
    
    optional_param = ToolConfigParameter(
        name="optional_param",
        param_type=ParameterType.INTEGER,
        description="Optional parameter",
        min_value=1,
        max_value=100
    )
    
    schema.add_parameter(required_param)
    schema.add_parameter(optional_param)
    
    # Valid config
    valid_config = {"required_param": "value", "optional_param": 50}
    is_valid, errors = schema.validate_config(valid_config)
    assert is_valid
    assert len(errors) == 0
    
    # Missing required parameter
    invalid_config1 = {"optional_param": 50}
    is_valid, errors = schema.validate_config(invalid_config1)
    assert not is_valid
    assert any("Required parameter 'required_param' is missing" in error for error in errors)
    
    # Invalid value
    invalid_config2 = {"required_param": "value", "optional_param": 200}
    is_valid, errors = schema.validate_config(invalid_config2)
    assert not is_valid
    assert any("Invalid value for parameter 'optional_param'" in error for error in errors)
    
    # Unknown parameter
    invalid_config3 = {"required_param": "value", "unknown_param": "value"}
    is_valid, errors = schema.validate_config(invalid_config3)
    assert not is_valid
    assert any("Unknown parameter 'unknown_param'" in error for error in errors)

def test_tool_config_schema_get_defaults():
    schema = ToolConfigSchema()
    
    param1 = ToolConfigParameter(
        name="param1",
        param_type=ParameterType.STRING,
        description="Parameter 1",
        default_value="default1"
    )
    
    param2 = ToolConfigParameter(
        name="param2",
        param_type=ParameterType.INTEGER,
        description="Parameter 2"
    )
    
    schema.add_parameter(param1)
    schema.add_parameter(param2)
    
    defaults = schema.get_defaults()
    assert defaults == {"param1": "default1"}

def test_tool_config_schema_to_dict():
    schema = ToolConfigSchema()
    param = ToolConfigParameter(
        name="test",
        param_type=ParameterType.STRING,
        description="Test parameter"
    )
    
    schema.add_parameter(param)
    result = schema.to_dict()
    
    assert "parameters" in result
    assert len(result["parameters"]) == 1
    assert result["parameters"][0]["name"] == "test"

def test_tool_config_schema_from_dict():
    schema_data = {
        "parameters": [
            {
                "name": "test",
                "type": "string",
                "description": "Test parameter",
                "required": False,
                "default_value": None,
                "enum_values": None,
                "min_value": None,
                "max_value": None,
                "pattern": None,
            }
        ]
    }
    
    schema = ToolConfigSchema.from_dict(schema_data)
    assert len(schema) == 1
    
    param = schema.get_parameter("test")
    assert param is not None
    assert param.name == "test"
    assert param.param_type == ParameterType.STRING
