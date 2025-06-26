import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from autobyteus.tools.functional_tool import FunctionalTool, tool, _parse_signature
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from typing import Optional, List, Dict, Any
import inspect

# --- Fixtures ---

@pytest.fixture
def clean_registry():
    """Provides a clean ToolRegistry for each test."""
    registry = ToolRegistry()
    original_defs = registry._definitions.copy()
    registry._definitions.clear()
    yield registry
    registry._definitions = original_defs

@pytest.fixture
def mock_agent_context():
    ctx = MagicMock(spec=AgentContext)
    ctx.agent_id = "functional_test_agent"
    return ctx

# --- Tests for FunctionalTool Class ---

@pytest.mark.asyncio
async def test_functional_tool_initialization_and_properties():
    """Tests that the FunctionalTool class initializes correctly and properties work."""
    mock_func = AsyncMock()
    mock_func.__name__ = 'mocked_init_func' # Add __name__ to the mock
    arg_schema = ParameterSchema()
    arg_schema.add_parameter(ParameterDefinition(name="p1", param_type=ParameterType.STRING, description="d"))

    tool_instance = FunctionalTool(
        original_func=mock_func,
        name="MyTestTool",
        description="A test description.",
        argument_schema=arg_schema,
        config_schema=None,
        is_async=True,
        expects_context=False,
        expects_tool_state=False,
        func_param_names=["p1"]
    )

    assert tool_instance.get_name() == "MyTestTool"
    assert tool_instance.get_description() == "A test description."
    assert tool_instance.get_argument_schema() == arg_schema
    assert tool_instance.get_config_schema() is None
    assert tool_instance._is_async is True
    assert tool_instance._original_func == mock_func
    assert hasattr(tool_instance, 'tool_state')
    assert isinstance(tool_instance.tool_state, dict)

@pytest.mark.asyncio
async def test_functional_tool_execute_async_func_with_state(mock_agent_context):
    """Tests executing an async function with context and tool_state."""
    mock_func = AsyncMock(return_value="async_result")
    mock_func.__name__ = 'mocked_async_func_for_exec' # Add __name__ to the mock
    tool_instance = FunctionalTool(
        original_func=mock_func,
        name="AsyncExecTool",
        description="d",
        argument_schema=ParameterSchema(),
        config_schema=None,
        is_async=True,
        expects_context=True,
        expects_tool_state=True,
        func_param_names=["arg1"]
    )
    # Set some initial state
    tool_instance.tool_state['counter'] = 5

    result = await tool_instance._execute(mock_agent_context, arg1="value1")
    
    assert result == "async_result"
    mock_func.assert_awaited_once_with(
        context=mock_agent_context, 
        tool_state={'counter': 5},
        arg1="value1"
    )

@pytest.mark.asyncio
async def test_functional_tool_execute_sync_func(mock_agent_context):
    """Tests executing a sync function via the FunctionalTool wrapper."""
    mock_func = MagicMock(return_value="sync_result")
    mock_func.__name__ = 'mocked_sync_func_for_exec' # Add __name__ to the mock
    tool_instance = FunctionalTool(
        original_func=mock_func,
        name="SyncExecTool",
        description="d",
        argument_schema=ParameterSchema(),
        config_schema=None,
        is_async=False,
        expects_context=False,
        expects_tool_state=False,
        func_param_names=["arg1"]
    )

    result = await tool_instance._execute(mock_agent_context, arg1="value1")
    
    assert result == "sync_result"
    mock_func.assert_called_once_with(arg1="value1")


# --- Tests for @tool Decorator ---

def test_tool_decorator_registers_definition(clean_registry: ToolRegistry):
    """Tests that the @tool decorator registers a ToolDefinition."""
    
    @tool(name="DecoratedTool")
    def my_decorated_func(p1: str):
        """Docstring for description."""
        pass
    
    definition = clean_registry.get_tool_definition("DecoratedTool")
    assert isinstance(definition, ToolDefinition)
    assert definition.name == "DecoratedTool"
    assert definition.description == "Docstring for description."
    assert callable(definition.custom_factory)
    assert definition.tool_class is None

def test_tool_decorator_returns_functional_tool_instance():
    """Tests that the decorator returns a ready-to-use instance."""
    
    @tool
    def another_decorated_func():
        pass
        
    assert isinstance(another_decorated_func, FunctionalTool)
    assert another_decorated_func.get_name() == "another_decorated_func"


@pytest.mark.asyncio
async def test_decorated_tool_is_executable(mock_agent_context):
    """Tests executing the instance returned by the decorator."""
    
    @tool
    async def executable_func(context: AgentContext, text: str) -> str:
        return f"executed: {text} by {context.agent_id}"
        
    result = await executable_func.execute(mock_agent_context, text="hello")
    assert result == "executed: hello by functional_test_agent"

@pytest.mark.asyncio
async def test_decorated_tool_with_state_persists(mock_agent_context):
    """Tests that state persists across calls to a stateful decorated tool."""
    
    @tool
    def stateful_counter(tool_state: Dict[str, Any]) -> int:
        """A simple counter tool that uses its state."""
        count = tool_state.get('count', 0)
        count += 1
        tool_state['count'] = count
        return count

    # Call 1
    result1 = await stateful_counter.execute(mock_agent_context)
    assert result1 == 1
    assert stateful_counter.tool_state['count'] == 1

    # Call 2
    result2 = await stateful_counter.execute(mock_agent_context)
    assert result2 == 2
    assert stateful_counter.tool_state['count'] == 2


# --- Tests for Schema Inference by _parse_signature ---

def test_parse_signature_simple_types():
    """Tests schema inference for basic types."""
    def func_simple(p_str: str, p_int: int, p_bool: bool, p_float: float): pass
    sig = inspect.signature(func_simple)
    
    _, expects_context, expects_tool_state, schema = _parse_signature(sig, "func_simple")
    
    assert expects_context is False
    assert expects_tool_state is False
    assert schema.get_parameter("p_str").param_type == ParameterType.STRING
    assert schema.get_parameter("p_int").param_type == ParameterType.INTEGER
    assert schema.get_parameter("p_bool").param_type == ParameterType.BOOLEAN
    assert schema.get_parameter("p_float").param_type == ParameterType.FLOAT
    assert all(p.required for p in schema.parameters)

def test_parse_signature_with_optional_and_defaults():
    """Tests schema inference for optional types and default values."""
    def func_optional(req_str: str, opt_int: Optional[int] = None, bool_default: bool = True): pass
    sig = inspect.signature(func_optional)
    
    _, _, _, schema = _parse_signature(sig, "func_optional")
    
    assert schema.get_parameter("req_str").required is True
    
    opt_int_param = schema.get_parameter("opt_int")
    assert opt_int_param.required is False
    assert opt_int_param.default_value is None
    assert opt_int_param.param_type == ParameterType.INTEGER

    bool_default_param = schema.get_parameter("bool_default")
    assert bool_default_param.required is False
    assert bool_default_param.default_value is True
    assert bool_default_param.param_type == ParameterType.BOOLEAN

def test_parse_signature_with_context_and_state():
    """Tests that 'context' and 'tool_state' are correctly identified and skipped."""
    def func_with_context(context: AgentContext, tool_state: dict, p1: str): pass
    sig = inspect.signature(func_with_context)
    
    param_names, expects_context, expects_tool_state, schema = _parse_signature(sig, "func_with_context")

    assert expects_context is True
    assert expects_tool_state is True
    assert param_names == ["p1"]
    assert schema.get_parameter("context") is None
    assert schema.get_parameter("tool_state") is None
    assert schema.get_parameter("p1") is not None
    assert len(schema.parameters) == 1

def test_parse_signature_with_collections():
    """Tests schema inference for list and dict."""
    def func_collections(p_list: List[str], p_dict: dict, p_untyped_list: list): pass
    sig = inspect.signature(func_collections)
    
    _, _, _, schema = _parse_signature(sig, "func_collections")
    
    list_param = schema.get_parameter("p_list")
    assert list_param.param_type == ParameterType.ARRAY
    assert list_param.array_item_schema == {"type": "string"}

    dict_param = schema.get_parameter("p_dict")
    assert dict_param.param_type == ParameterType.OBJECT

    untyped_list_param = schema.get_parameter("p_untyped_list")
    assert untyped_list_param.param_type == ParameterType.ARRAY
    assert untyped_list_param.array_item_schema is True # Generic array
