
import pytest
from pydantic import Field
from autobyteus.tools.functional_tool import tool
from autobyteus.utils.parameter_schema import ParameterType

class TestFunctionalToolFieldSupport:
    
    def test_field_description_extraction(self):
        """Test that Field(description=...) is correctly extracted."""
        
        @tool(name="test_tool")
        def my_tool(arg1: str = Field(..., description="Custom description for arg1")):
            pass
            
        # The decorator returns the instance directly
        tool_instance = my_tool
        schema = tool_instance.get_argument_schema()
        param = schema.get_parameter("arg1")
        
        assert param is not None
        assert param.description == "Custom description for arg1"
        assert param.required is True # ... means required

    def test_field_default_value(self):
        """Test that Field(default=...) is correctly handled."""
        
        @tool(name="test_tool_default")
        def my_tool_default(arg1: int = Field(42, description="An integer")):
            pass
            
        tool_instance = my_tool_default
        schema = tool_instance.get_argument_schema()
        param = schema.get_parameter("arg1")
        
        assert param is not None
        assert param.default_value == 42
        assert param.required is False

    def test_field_implicit_required(self):
        """Test that Field() without default implies required (PydanticUndefined)."""
        
        @tool(name="test_tool_req")
        def my_tool_req(arg1: str = Field(description="Required")):
            pass
            
        tool_instance = my_tool_req
        schema = tool_instance.get_argument_schema()
        param = schema.get_parameter("arg1")
        
        # Pydantic Field() defaults to Undefined if not provided, making it required
        assert param.required is True
        assert param.default_value is None

    def test_mixed_usage(self):
        """Test mixed usage of standard args and Field args."""
        
        @tool(name="test_mixed")
        def my_tool_mixed(
            path: str, # Should get auto-path description
            count: int = 10, # Standard default
            force: bool = Field(False, description="Force overwrite") # Field with default
        ):
            pass
            
        tool_instance = my_tool_mixed
        schema = tool_instance.get_argument_schema()
        
        # Check path
        p_path = schema.get_parameter("path")
        assert "expected to be a path" in p_path.description
        assert p_path.required is True
        
        # Check count
        p_count = schema.get_parameter("count")
        assert p_count.default_value == 10
        assert p_count.required is False
        
        # Check force
        p_force = schema.get_parameter("force")
        assert p_force.description == "Force overwrite"
        assert p_force.default_value is False
        assert p_force.required is False
