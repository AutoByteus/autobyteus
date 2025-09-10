# file: autobyteus/tests/unit_tests/tools/usage/formatters/test_default_json_example_formatter.py
import pytest

from autobyteus.tools.usage.formatters.default_json_example_formatter import DefaultJsonExampleFormatter
from autobyteus.tools.registry import ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

@pytest.fixture
def formatter():
    return DefaultJsonExampleFormatter()

# --- Fixture for a tool with various primitive types ---
@pytest.fixture
def primitives_tool_def():
    """A tool definition with a variety of primitive argument types."""
    schema = ParameterSchema()
    schema.add_parameter(ParameterDefinition(name="input_path", param_type=ParameterType.STRING, description="Input path.", required=True))
    schema.add_parameter(ParameterDefinition(name="output_path", param_type=ParameterType.STRING, description="Output path.", required=False))
    schema.add_parameter(ParameterDefinition(name="retries", param_type=ParameterType.INTEGER, description="Number of retries.", required=False, default_value=3))
    schema.add_parameter(ParameterDefinition(name="threshold", param_type=ParameterType.FLOAT, description="Confidence threshold.", required=True))
    schema.add_parameter(ParameterDefinition(name="verbose", param_type=ParameterType.BOOLEAN, description="Enable verbose logging.", required=True))
    schema.add_parameter(ParameterDefinition(name="mode", param_type=ParameterType.ENUM, description="Processing mode.", required=True, enum_values=["fast", "slow", "balanced"]))

    return ToolDefinition(
        name="PrimitivesTool",
        description="A tool with various primitive types.",
        argument_schema=schema,
        tool_class=BaseTool, # A dummy class is sufficient
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

# --- Fixture for a tool with a nested object ---
@pytest.fixture
def nested_object_tool_def():
    """A tool definition with a nested object argument."""
    person_schema = ParameterSchema()
    person_schema.add_parameter(ParameterDefinition(name="name", param_type=ParameterType.STRING, description="Name.", required=True))
    person_schema.add_parameter(ParameterDefinition(name="age", param_type=ParameterType.INTEGER, description="Age.", required=True))

    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(name="user", param_type=ParameterType.OBJECT, description="User object.", required=True, object_schema=person_schema))

    return ToolDefinition(
        name="NestedObjectTool",
        description="A tool with a nested object.",
        argument_schema=main_schema,
        tool_class=BaseTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

# --- Fixture for a tool with an array of objects ---
@pytest.fixture
def array_of_objects_tool_def():
    """A tool definition with an array of objects."""
    item_schema = ParameterSchema()
    item_schema.add_parameter(ParameterDefinition(name="id", param_type=ParameterType.STRING, description="Item ID.", required=True))
    item_schema.add_parameter(ParameterDefinition(name="quantity", param_type=ParameterType.INTEGER, description="Item quantity.", required=True))

    main_schema = ParameterSchema()
    main_schema.add_parameter(ParameterDefinition(name="items", param_type=ParameterType.ARRAY, description="List of items.", required=True, array_item_schema=item_schema))

    return ToolDefinition(
        name="ArrayOfObjectsTool",
        description="A tool with an array of objects.",
        argument_schema=main_schema,
        tool_class=BaseTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )
    
# --- Test Cases ---

def test_provide_example_for_primitives_tool(formatter: DefaultJsonExampleFormatter, primitives_tool_def: ToolDefinition):
    """Tests example generation for a tool with various primitive types."""
    json_output = formatter.provide(primitives_tool_def)
    
    assert "tool" in json_output
    tool_call = json_output["tool"]
    
    assert tool_call["function"] == "PrimitivesTool"
    
    # Should include required fields and optional fields with defaults
    expected_params = {
        "input_path": "example_input_path",
        "retries": 3,
        "threshold": 123.45,
        "verbose": True,
        "mode": "fast"
    }
    assert tool_call["parameters"] == expected_params

def test_provide_example_for_tool_with_nested_object(formatter: DefaultJsonExampleFormatter, nested_object_tool_def: ToolDefinition):
    """Tests that a nested object argument is formatted correctly."""
    json_output = formatter.provide(nested_object_tool_def)
    
    tool_call = json_output["tool"]
    assert tool_call["function"] == "NestedObjectTool"
    
    expected_params = {
        "user": {
            "name": "example_string",
            "age": 1
        }
    }
    assert tool_call["parameters"] == expected_params

def test_provide_example_for_tool_with_array_of_objects(formatter: DefaultJsonExampleFormatter, array_of_objects_tool_def: ToolDefinition):
    """Tests that an array of objects is formatted correctly."""
    json_output = formatter.provide(array_of_objects_tool_def)

    tool_call = json_output["tool"]
    assert tool_call["function"] == "ArrayOfObjectsTool"

    expected_params = {
        "items": [
            {
                "id": "example_string",
                "quantity": 1
            }
        ]
    }
    assert tool_call["parameters"] == expected_params

def test_provide_example_for_tool_with_no_arguments(formatter: DefaultJsonExampleFormatter):
    """Tests a tool that has no arguments."""
    no_args_def = ToolDefinition(
        name="NoArgsTool",
        description="A tool with no arguments.",
        argument_schema=None,
        tool_class=BaseTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )
    json_output = formatter.provide(no_args_def)

    tool_call = json_output["tool"]
    assert tool_call["function"] == "NoArgsTool"
    assert tool_call["parameters"] == {}
