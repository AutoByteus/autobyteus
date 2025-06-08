import pytest
import re 

from autobyteus.tools.parameter_schema import (
    ParameterDefinition,
    ParameterSchema,
    ParameterType
)

class TestParameterDefinition:
    def test_basic_initialization(self):
        pd = ParameterDefinition(name="test_param", param_type=ParameterType.STRING, description="A test string.")
        assert pd.name == "test_param"
        assert pd.param_type == ParameterType.STRING
        assert pd.description == "A test string."
        assert pd.required is False
        assert pd.default_value is None
        assert pd.enum_values is None
        assert pd.array_item_schema is None

    def test_initialization_object_type(self):
        pd = ParameterDefinition(name="obj_param", param_type=ParameterType.OBJECT, description="An object param.")
        assert pd.param_type == ParameterType.OBJECT
        assert pd.array_item_schema is None 

    def test_initialization_array_type_generic(self):
        pd = ParameterDefinition(name="arr_param_generic", param_type=ParameterType.ARRAY, description="A generic array.")
        assert pd.param_type == ParameterType.ARRAY
        assert pd.array_item_schema is None 

    def test_initialization_array_type_with_item_schema(self):
        item_schema = {"type": "string"}
        pd = ParameterDefinition(name="arr_param_typed", param_type=ParameterType.ARRAY, description="An array of strings.", array_item_schema=item_schema)
        assert pd.param_type == ParameterType.ARRAY
        assert pd.array_item_schema == item_schema

    def test_post_init_validations(self):
        with pytest.raises(ValueError, match="ParameterDefinition name must be a non-empty string"):
            ParameterDefinition(name="", param_type=ParameterType.STRING, description="Test")
        
        with pytest.raises(ValueError, match="must have a non-empty description"):
            ParameterDefinition(name="test", param_type=ParameterType.STRING, description="")

        with pytest.raises(ValueError, match="of type ENUM must specify enum_values"):
            ParameterDefinition(name="enum_param", param_type=ParameterType.ENUM, description="Test")

        with pytest.raises(ValueError, match="array_item_schema should only be provided if param_type is ARRAY"):
            ParameterDefinition(name="str_param", param_type=ParameterType.STRING, description="Test", array_item_schema={"type": "number"})
            
        assert ParameterDefinition(name="valid_enum", param_type=ParameterType.ENUM, description="Valid", enum_values=["a", "b"]) is not None

    def test_validate_value_string(self):
        pd_string = ParameterDefinition(name="s", param_type=ParameterType.STRING, description="d")
        assert pd_string.validate_value("hello") is True
        assert pd_string.validate_value(123) is False
        assert pd_string.validate_value(None) is True 

        pd_string_req = ParameterDefinition(name="s_req", param_type=ParameterType.STRING, description="d_req", required=True)
        assert pd_string_req.validate_value(None) is False
        assert pd_string_req.validate_value("") is True 

        pd_string_pattern = ParameterDefinition(name="s_pat", param_type=ParameterType.STRING, description="d_pat", pattern="^[a-z]+$")
        assert pd_string_pattern.validate_value("abc") is True
        assert pd_string_pattern.validate_value("aBc") is False

    def test_validate_value_integer(self):
        pd_int = ParameterDefinition(name="i", param_type=ParameterType.INTEGER, description="d", min_value=0, max_value=10)
        assert pd_int.validate_value(5) is True
        assert pd_int.validate_value(0) is True
        assert pd_int.validate_value(10) is True
        assert pd_int.validate_value(-1) is False
        assert pd_int.validate_value(11) is False
        assert pd_int.validate_value(5.5) is False
        assert pd_int.validate_value("text") is False
        assert pd_int.validate_value(True) is False 

    def test_validate_value_float(self):
        pd_float = ParameterDefinition(name="f", param_type=ParameterType.FLOAT, description="d", min_value=0.0, max_value=1.0)
        assert pd_float.validate_value(0.5) is True
        assert pd_float.validate_value(0) is True 
        assert pd_float.validate_value(1.0) is True
        assert pd_float.validate_value(-0.1) is False
        assert pd_float.validate_value(1.1) is False
        assert pd_float.validate_value("text") is False
    
    def test_validate_value_boolean(self):
        pd_bool = ParameterDefinition(name="b", param_type=ParameterType.BOOLEAN, description="d")
        assert pd_bool.validate_value(True) is True
        assert pd_bool.validate_value(False) is True
        assert pd_bool.validate_value(0) is False
        assert pd_bool.validate_value("True") is False

    def test_validate_value_enum(self):
        pd_enum = ParameterDefinition(name="e", param_type=ParameterType.ENUM, description="d", enum_values=["cat", "dog"])
        assert pd_enum.validate_value("cat") is True
        assert pd_enum.validate_value("dog") is True
        assert pd_enum.validate_value("fish") is False
        assert pd_enum.validate_value(None) is True 

    def test_validate_value_object(self):
        pd_object = ParameterDefinition(name="obj", param_type=ParameterType.OBJECT, description="d")
        assert pd_object.validate_value({"key": "value"}) is True
        assert pd_object.validate_value({}) is True 
        assert pd_object.validate_value(["not", "a", "dict"]) is False
        assert pd_object.validate_value("string") is False
        assert pd_object.validate_value(None) is True 

        pd_object_req = ParameterDefinition(name="obj_req", param_type=ParameterType.OBJECT, description="d_req", required=True)
        assert pd_object_req.validate_value(None) is False

    def test_validate_value_array(self):
        pd_array = ParameterDefinition(name="arr", param_type=ParameterType.ARRAY, description="d")
        assert pd_array.validate_value([1, "two", True]) is True
        assert pd_array.validate_value([]) is True 
        assert pd_array.validate_value({"not": "a_list"}) is False
        assert pd_array.validate_value("string") is False
        assert pd_array.validate_value(None) is True 

        pd_array_req = ParameterDefinition(name="arr_req", param_type=ParameterType.ARRAY, description="d_req", required=True)
        assert pd_array_req.validate_value(None) is False

    def test_to_dict_serialization(self):
        item_schema = {"type": "integer"}
        pd = ParameterDefinition(
            name="complex_array", 
            param_type=ParameterType.ARRAY, 
            description="Array of ints",
            required=True,
            default_value=[1,2], 
            array_item_schema=item_schema,
            min_value=5 
        )
        d = pd.to_dict()
        assert d["name"] == "complex_array"
        assert d["type"] == "array"
        assert d["array_item_schema"] == item_schema
        assert d["required"] is True
        assert d["default_value"] == [1,2]
        assert d["min_value"] == 5 

        pd_simple = ParameterDefinition(name="s", param_type=ParameterType.STRING, description="d")
        d_simple = pd_simple.to_dict()
        assert "array_item_schema" not in d_simple 

    def test_to_json_schema_property_dict_object(self):
        pd_object = ParameterDefinition(name="obj_param", param_type=ParameterType.OBJECT, description="An object param.")
        json_schema = pd_object.to_json_schema_property_dict()
        assert json_schema == {"type": "object", "description": "An object param."}
        
        pd_object_def = ParameterDefinition(name="obj_def", param_type=ParameterType.OBJECT, description="An object with default.", default_value={"a":1})
        json_schema_def = pd_object_def.to_json_schema_property_dict()
        assert json_schema_def == {"type": "object", "description": "An object with default.", "default": {"a":1}}


    def test_to_json_schema_property_dict_array(self):
        pd_array_generic = ParameterDefinition(name="arr_gen", param_type=ParameterType.ARRAY, description="Generic array")
        json_schema_gen = pd_array_generic.to_json_schema_property_dict()
        assert json_schema_gen == {"type": "array", "description": "Generic array", "items": True}

        item_schema = {"type": "string"}
        pd_array_typed = ParameterDefinition(name="arr_typed", param_type=ParameterType.ARRAY, description="Typed array", array_item_schema=item_schema)
        json_schema_typed = pd_array_typed.to_json_schema_property_dict()
        assert json_schema_typed == {"type": "array", "description": "Typed array", "items": item_schema}
        
        pd_array_def = ParameterDefinition(name="arr_def", param_type=ParameterType.ARRAY, description="Array with default", default_value=[1,2])
        json_schema_def = pd_array_def.to_json_schema_property_dict()
        assert json_schema_def == {"type": "array", "description": "Array with default", "items": True, "default": [1,2]}


class TestParameterSchema:
    def test_add_parameter_and_get_parameter(self):
        schema = ParameterSchema()
        pd1 = ParameterDefinition(name="p1", param_type=ParameterType.STRING, description="d1")
        pd2 = ParameterDefinition(name="p2", param_type=ParameterType.INTEGER, description="d2")
        
        schema.add_parameter(pd1)
        schema.add_parameter(pd2)

        assert schema.get_parameter("p1") == pd1
        assert schema.get_parameter("p2") == pd2
        assert schema.get_parameter("p3") is None
        assert len(schema) == 2
        assert bool(schema) is True

    def test_add_duplicate_parameter_raises_error(self):
        schema = ParameterSchema()
        pd1 = ParameterDefinition(name="p1", param_type=ParameterType.STRING, description="d1")
        schema.add_parameter(pd1)
        with pytest.raises(ValueError, match="Parameter 'p1' already exists in schema"):
            schema.add_parameter(pd1) 
        
        pd1_again = ParameterDefinition(name="p1", param_type=ParameterType.INTEGER, description="d1_other")
        with pytest.raises(ValueError, match="Parameter 'p1' already exists in schema"):
            schema.add_parameter(pd1_again) 

    def test_validate_config_basic_types(self): 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="name", param_type=ParameterType.STRING, description="d_name", required=True))
        schema.add_parameter(ParameterDefinition(name="age", param_type=ParameterType.INTEGER, description="d_age", required=False, min_value=0))
        
        valid_config_data = {"name": "Alice", "age": 30}
        is_valid, errors = schema.validate_config(valid_config_data)
        assert is_valid is True
        assert not errors

        invalid_config_missing = {"age": 30}
        is_valid, errors = schema.validate_config(invalid_config_missing)
        assert is_valid is False
        assert "Required parameter 'name' is missing." in errors

        invalid_config_type = {"name": "Bob", "age": "thirty"} 
        is_valid, errors = schema.validate_config(invalid_config_type)
        assert is_valid is False
        assert any("Invalid value for parameter 'age'" in e for e in errors)
        
        config_with_unknown = {"name": "Eve", "unknown_param": "test"}
        is_valid, errors = schema.validate_config(config_with_unknown)
        assert is_valid is True 
        assert not errors

    def test_validate_config_with_object_and_array(self):
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="tags", 
            param_type=ParameterType.ARRAY, 
            description="List of tags", 
            array_item_schema={"type": "string"},
            required=True 
        ))
        schema.add_parameter(ParameterDefinition(
            name="profile", 
            param_type=ParameterType.OBJECT, 
            description="User profile object",
            required=False
        ))
        schema.add_parameter(ParameterDefinition(
            name="history",
            param_type=ParameterType.ARRAY,
            description="Event history (array of objects)",
            array_item_schema={"type": "object", "properties": {"event_name": {"type": "string"}, "timestamp": {"type": "string"}}}
        ))

        valid_data = {
            "tags": ["alpha", "beta"],
            "profile": {"user_id": 123, "active": True},
            "history": [{"event_name": "login", "timestamp": "2023-01-01T10:00:00Z"}]
        }
        is_valid, errors = schema.validate_config(valid_data)
        assert is_valid is True, f"Errors: {errors}"
        assert not errors

        invalid_data_tags_type = {
            "tags": "alpha,beta", 
            "profile": {"user_id": 123}
        }
        is_valid, errors = schema.validate_config(invalid_data_tags_type)
        assert is_valid is False
        assert any("Invalid value for parameter 'tags'" in e for e in errors)

        invalid_data_profile_type = {
            "tags": ["gamma"],
            "profile": "user_profile_string" 
        }
        is_valid, errors = schema.validate_config(invalid_data_profile_type)
        assert is_valid is False
        assert any("Invalid value for parameter 'profile'" in e for e in errors)
        
        valid_data_no_profile = {
            "tags": ["delta"]
        }
        is_valid, errors = schema.validate_config(valid_data_no_profile)
        assert is_valid is True
        assert not errors

        invalid_data_no_tags = {
            "profile": {"user_id": 456}
        }
        is_valid, errors = schema.validate_config(invalid_data_no_tags)
        assert is_valid is False
        assert "Required parameter 'tags' is missing." in errors
        
        valid_data_history_items = {
            "tags": ["epsilon"],
            "history": [{"event_name": "click"}, {"event_name": "purchase", "value": 100}]
        }
        is_valid, errors = schema.validate_config(valid_data_history_items)
        assert is_valid is True, f"Errors for history items: {errors}"
        assert not errors


    def test_get_defaults(self):
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="p1", param_type=ParameterType.STRING, description="d1", default_value="hello"))
        schema.add_parameter(ParameterDefinition(name="p2", param_type=ParameterType.INTEGER, description="d2")) 
        schema.add_parameter(ParameterDefinition(name="p3", param_type=ParameterType.BOOLEAN, description="d3", default_value=False))
        
        defaults = schema.get_defaults()
        assert defaults == {"p1": "hello", "p3": False}

    def test_to_dict_and_from_dict_roundtrip(self):
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="p_str", param_type=ParameterType.STRING, description="d_str"))
        schema.add_parameter(ParameterDefinition(
            name="p_arr", 
            param_type=ParameterType.ARRAY, 
            description="d_arr", 
            array_item_schema={"type": "number"}, 
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="p_obj", 
            param_type=ParameterType.OBJECT, 
            description="d_obj", 
            default_value={"a": 1}
        ))

        schema_dict = schema.to_dict()
        
        rehydrated_schema = ParameterSchema.from_dict(schema_dict)

        assert len(rehydrated_schema.parameters) == 3
        p_str_re = rehydrated_schema.get_parameter("p_str")
        assert p_str_re and p_str_re.param_type == ParameterType.STRING
        
        p_arr_re = rehydrated_schema.get_parameter("p_arr")
        assert p_arr_re and p_arr_re.param_type == ParameterType.ARRAY
        assert p_arr_re.array_item_schema == {"type": "number"}
        assert p_arr_re.required is True
        
        p_obj_re = rehydrated_schema.get_parameter("p_obj")
        assert p_obj_re and p_obj_re.param_type == ParameterType.OBJECT
        assert p_obj_re.default_value == {"a": 1}

    def test_to_json_schema_dict_full_with_object_array(self): 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="name", param_type=ParameterType.STRING, description="User's name", required=True))
        schema.add_parameter(ParameterDefinition(name="scores", param_type=ParameterType.ARRAY, description="List of scores", array_item_schema={"type": "integer"}))
        schema.add_parameter(ParameterDefinition(name="settings", param_type=ParameterType.OBJECT, description="User settings"))
        schema.add_parameter(ParameterDefinition(name="mode", param_type=ParameterType.ENUM, description="Mode", enum_values=["A", "B"], default_value="A"))
        schema.add_parameter(ParameterDefinition(
            name="items_log", 
            param_type=ParameterType.ARRAY, 
            description="Log of items", 
            array_item_schema={"type": "object", "properties": {"id": {"type": "string"}, "value": {"type": "number"}}}
        ))
        schema.add_parameter(ParameterDefinition(
            name="generic_obj_list",
            param_type=ParameterType.ARRAY,
            description="List of generic objects",
            array_item_schema={"type": "object"} 
        ))
        schema.add_parameter(ParameterDefinition(
            name="untyped_list",
            param_type=ParameterType.ARRAY,
            description="Untyped list (items: true)"
        ))


        json_schema = schema.to_json_schema_dict()
        
        expected_json_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User's name"},
                "scores": {"type": "array", "description": "List of scores", "items": {"type": "integer"}},
                "settings": {"type": "object", "description": "User settings"},
                "mode": {"type": "string", "description": "Mode", "enum": ["A", "B"], "default": "A"},
                "items_log": {
                    "type": "array", 
                    "description": "Log of items", 
                    "items": {"type": "object", "properties": {"id": {"type": "string"}, "value": {"type": "number"}}}
                },
                "generic_obj_list": {
                    "type": "array",
                    "description": "List of generic objects",
                    "items": {"type": "object"}
                },
                "untyped_list": {
                    "type": "array",
                    "description": "Untyped list (items: true)",
                    "items": True
                }
            },
            "required": ["name"]
        }
        assert json_schema == expected_json_schema
    
    def test_to_json_schema_dict_empty_schema(self):
        schema = ParameterSchema()
        json_schema = schema.to_json_schema_dict()
        assert json_schema == {"type": "object", "properties": {}, "required": []}

    def test_empty_schema_properties(self):
        schema = ParameterSchema()
        assert len(schema) == 0
        assert bool(schema) is False
        assert schema.get_parameter("non_existent") is None
        assert schema.get_defaults() == {}

    def test_parameter_type_to_json_schema_type(self):
        assert ParameterType.STRING.to_json_schema_type() == "string"
        assert ParameterType.INTEGER.to_json_schema_type() == "integer"
        assert ParameterType.FLOAT.to_json_schema_type() == "number"
        assert ParameterType.BOOLEAN.to_json_schema_type() == "boolean"
        assert ParameterType.ENUM.to_json_schema_type() == "string"
        # REMOVED: Assertions for FILE_PATH and DIRECTORY_PATH
        # assert ParameterType.FILE_PATH.to_json_schema_type() == "string"
        # assert ParameterType.DIRECTORY_PATH.to_json_schema_type() == "string"
        assert ParameterType.OBJECT.to_json_schema_type() == "object"
        assert ParameterType.ARRAY.to_json_schema_type() == "array"
