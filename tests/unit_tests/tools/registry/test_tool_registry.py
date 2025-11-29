# file: autobyteus/tests/unit_tests/tools/registry/test_tool_registry.py
import pytest
from typing import Optional, Any, Dict
from unittest.mock import MagicMock

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.functional_tool import tool, FunctionalTool
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.tools.registry import ToolRegistry, ToolDefinition, default_tool_registry
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_origin import ToolOrigin
from autobyteus.tools.tool_category import ToolCategory

# --- Dummy Tools for Testing ---

class DummyToolNoConfig(BaseTool):
    """A simple tool that doesn't use configuration."""
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        self.config_received = config

    @classmethod
    def get_name(cls) -> str: return "DummyToolNoConfig"
    @classmethod
    def get_description(cls) -> str: return "A dummy tool without config."
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None
    async def _execute(self, context: Any, **kwargs) -> Any: return "executed"

class DummyToolWithConfig(BaseTool):
    """A tool that uses a ToolConfig object."""
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        self.value = "default"
        if config:
            self.value = config.get("value", "default")

    @classmethod
    def get_name(cls) -> str: return "DummyToolWithConfig"
    @classmethod
    def get_description(cls) -> str: return "A dummy tool with config."
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None
    async def _execute(self, context: Any, **kwargs) -> Any: return self.value

class DummyToolFailsInit(BaseTool):
    """A tool that always fails on instantiation."""
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        raise ValueError("Initialization failed")

    @classmethod
    def get_name(cls) -> str: return "DummyToolFailsInit"
    @classmethod
    def get_description(cls) -> str: return "A tool that fails to initialize."
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None
    async def _execute(self, context: Any, **kwargs) -> Any: pass

class DummyFactoryTool(BaseTool):
    """A tool created by a factory."""
    def __init__(self, source: str, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        self.source = source

    @classmethod
    def get_name(cls) -> str: return "DummyFactoryTool"
    @classmethod
    def get_description(cls) -> str: return "A dummy tool created by a factory."
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None
    async def _execute(self, context: Any, **kwargs) -> Any: return f"created from {self.source}"

class DynamicDescriptionTool(BaseTool):
    """A tool whose description can change at runtime."""
    desc_text = "Initial description"

    @classmethod
    def get_name(cls) -> str: return "DynamicDescriptionTool"
    @classmethod
    def get_description(cls) -> str: return cls.desc_text
    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]: return None
    async def _execute(self, context: Any, **kwargs) -> Any: return self.desc_text

def dummy_factory(config: Optional[ToolConfig] = None) -> DummyFactoryTool:
    """Factory function for creating DummyFactoryTool."""
    source = "factory_default"
    if config and config.get("source_override"):
        source = config.get("source_override")
    return DummyFactoryTool(source=source, config=config)

# --- Pytest Fixtures ---

@pytest.fixture(autouse=True)
def clean_registry():
    """
    Ensures the global default_tool_registry is clean for each test by directly
    manipulating the singleton's class-level dictionary. This avoids issues
    with instance swapping and test pollution from import-time decorators.
    """
    original_defs = ToolRegistry._definitions.copy()
    ToolRegistry._definitions.clear()
    yield
    ToolRegistry._definitions.clear()
    ToolRegistry._definitions.update(original_defs)


@pytest.fixture
def no_config_def() -> ToolDefinition:
    """Fixture for DummyToolNoConfig's definition using the new constructor."""
    return ToolDefinition(
        name="DummyToolNoConfig",
        description="A dummy tool without config.",
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        tool_class=DummyToolNoConfig,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

@pytest.fixture
def with_config_def() -> ToolDefinition:
    """Fixture for DummyToolWithConfig's definition using the new constructor."""
    return ToolDefinition(
        name="DummyToolWithConfig",
        description="A dummy tool with config.",
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        tool_class=DummyToolWithConfig,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

@pytest.fixture
def factory_def() -> ToolDefinition:
    """Fixture for the factory-based tool's definition using the new constructor."""
    return ToolDefinition(
        name="DummyFactoryTool",
        description="A dummy tool created by a factory.",
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        custom_factory=dummy_factory,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )

# --- Test Cases ---

def test_singleton_instance():
    """Tests that ToolRegistry is a singleton."""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()
    assert registry1 is registry2

def test_register_and_get_tool_definition(no_config_def: ToolDefinition):
    """Tests registering a tool and retrieving its definition."""
    assert default_tool_registry.get_tool_definition("DummyToolNoConfig") is None
    default_tool_registry.register_tool(no_config_def)
    retrieved_def = default_tool_registry.get_tool_definition("DummyToolNoConfig")
    assert retrieved_def is no_config_def
    assert retrieved_def.name == "DummyToolNoConfig"

def test_register_overwrites_existing(no_config_def: ToolDefinition):
    """Tests that registering a tool with an existing name overwrites the old one."""
    default_tool_registry.register_tool(no_config_def)
    
    new_def = ToolDefinition(
        name="DummyToolNoConfig", # Same name
        description="An updated description.",
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        tool_class=DummyToolNoConfig,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )
    default_tool_registry.register_tool(new_def)
    
    retrieved_def = default_tool_registry.get_tool_definition("DummyToolNoConfig")
    assert retrieved_def is not no_config_def
    assert retrieved_def.description == "An updated description."

def test_unregister_tool(no_config_def: ToolDefinition):
    """Tests the unregister_tool method."""
    tool_name = no_config_def.name
    default_tool_registry.register_tool(no_config_def)
    
    # Verify it's there
    assert default_tool_registry.get_tool_definition(tool_name) is not None
    
    # Unregister and verify it's gone
    result = default_tool_registry.unregister_tool(tool_name)
    assert result is True
    assert default_tool_registry.get_tool_definition(tool_name) is None
    
    # Test unregistering a non-existent tool
    result_nonexistent = default_tool_registry.unregister_tool("nonexistent_tool")
    assert result_nonexistent is False

def test_reload_tool_schema():
    """Tests eagerly reloading the schema for a single tool."""
    mock_provider = MagicMock(return_value=ParameterSchema())
    tool_def = ToolDefinition(
        name="ReloadableTool",
        description="A tool to test reloading.",
        argument_schema_provider=mock_provider,
        config_schema_provider=lambda: None,
        tool_class=DummyToolNoConfig,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
    )
    default_tool_registry.register_tool(tool_def)

    # First access, populates cache
    _ = tool_def.argument_schema
    mock_provider.assert_called_once()

    # Second access, should be cached
    _ = tool_def.argument_schema
    mock_provider.assert_called_once()

    # Reload the schema via the registry. This should be an eager operation.
    result = default_tool_registry.reload_tool_schema("ReloadableTool")
    assert result is True
    assert mock_provider.call_count == 2
    
    # Third access, should be cached again
    _ = tool_def.argument_schema
    assert mock_provider.call_count == 2
    
    # Test reloading a non-existent tool
    result_nonexistent = default_tool_registry.reload_tool_schema("nonexistent")
    assert result_nonexistent is False

def test_reload_tool_schema_updates_description():
    """Tests that reload_tool_schema also refreshes a tool's description."""
    DynamicDescriptionTool.desc_text = "Initial description"
    tool_def = ToolDefinition(
        name=DynamicDescriptionTool.get_name(),
        description=DynamicDescriptionTool.get_description(),
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        tool_class=DynamicDescriptionTool,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
    )
    default_tool_registry.register_tool(tool_def)

    assert tool_def.description == "Initial description"

    # Mutate the class-level description and reload.
    DynamicDescriptionTool.desc_text = "Updated description"
    default_tool_registry.reload_tool_schema(DynamicDescriptionTool.get_name())

    assert tool_def.description == "Updated description"

def test_reload_all_tool_schemas():
    """Tests eagerly reloading schemas for all registered tools."""
    mock_provider1 = MagicMock(return_value=ParameterSchema())
    mock_provider2 = MagicMock(return_value=ParameterSchema())
    
    tool_def1 = ToolDefinition(
        name="Tool1",
        description="d1",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=mock_provider1,
        config_schema_provider=lambda: None,
        tool_class=DummyToolNoConfig
    )
    tool_def2 = ToolDefinition(
        name="Tool2",
        description="d2",
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL,
        argument_schema_provider=mock_provider2,
        config_schema_provider=lambda: None,
        tool_class=DummyToolNoConfig
    )
    
    default_tool_registry.register_tool(tool_def1)
    default_tool_registry.register_tool(tool_def2)

    # Access both to populate cache
    _ = tool_def1.argument_schema
    _ = tool_def2.argument_schema
    mock_provider1.assert_called_once()
    mock_provider2.assert_called_once()

    # Reload all. This should be an eager operation.
    default_tool_registry.reload_all_tool_schemas()
    assert mock_provider1.call_count == 2
    assert mock_provider2.call_count == 2

    # Access again, should be cached
    _ = tool_def1.argument_schema
    _ = tool_def2.argument_schema
    assert mock_provider1.call_count == 2
    assert mock_provider2.call_count == 2

def test_list_tools(no_config_def: ToolDefinition, factory_def: ToolDefinition):
    """Tests listing registered tools."""
    assert default_tool_registry.list_tools() == []
    assert default_tool_registry.list_tool_names() == []
    
    default_tool_registry.register_tool(no_config_def)
    default_tool_registry.register_tool(factory_def)
    
    defs = default_tool_registry.list_tools()
    names = default_tool_registry.list_tool_names()
    
    assert len(defs) == 2
    assert len(names) == 2
    assert "DummyToolNoConfig" in names
    assert "DummyFactoryTool" in names

def test_create_simple_class_based_tool(no_config_def: ToolDefinition):
    """Tests creating a simple tool from its class without config."""
    default_tool_registry.register_tool(no_config_def)
    tool_instance = default_tool_registry.create_tool("DummyToolNoConfig")
    
    assert isinstance(tool_instance, DummyToolNoConfig)
    assert tool_instance.config_received is None

@pytest.mark.asyncio
async def test_create_class_based_tool_with_config(with_config_def: ToolDefinition):
    """Tests creating a class-based tool, passing a ToolConfig."""
    default_tool_registry.register_tool(with_config_def)
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-for-config-tool"
    
    # Create without config
    tool_instance_default = default_tool_registry.create_tool("DummyToolWithConfig")
    assert isinstance(tool_instance_default, DummyToolWithConfig)
    assert await tool_instance_default.execute(mock_context) == "default"

    # Create with config
    config = ToolConfig(params={"value": "custom_value"})
    tool_instance_custom = default_tool_registry.create_tool("DummyToolWithConfig", config=config)
    assert isinstance(tool_instance_custom, DummyToolWithConfig)
    assert await tool_instance_custom.execute(mock_context) == "custom_value"

@pytest.mark.asyncio
async def test_create_factory_based_tool(factory_def: ToolDefinition):
    """Tests creating a tool using a custom factory."""
    default_tool_registry.register_tool(factory_def)
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-for-factory-tool"

    # Create without config
    tool_instance_default = default_tool_registry.create_tool("DummyFactoryTool")
    assert isinstance(tool_instance_default, DummyFactoryTool)
    assert await tool_instance_default.execute(mock_context) == "created from factory_default"
    assert tool_instance_default._config is None

    # Create with config passed to factory
    config = ToolConfig(params={"source_override": "factory_custom"})
    tool_instance_custom = default_tool_registry.create_tool("DummyFactoryTool", config=config)
    assert isinstance(tool_instance_custom, DummyFactoryTool)
    assert await tool_instance_custom.execute(mock_context) == "created from factory_custom"
    assert tool_instance_custom._config is not None

@pytest.mark.asyncio
async def test_create_functional_tool_from_registry():
    """Tests creating a functional tool instance from the registry after the refactor."""
    # Define the tool inside the test to avoid import-time registration
    @tool(name="MyFunctionalTool")
    async def dummy_func(context: Any, text: str) -> str:
        """A simple functional tool for testing."""
        return f"processed: {text}"
    
    # 1. Verify it was registered with the correct definition type
    definition = default_tool_registry.get_tool_definition("MyFunctionalTool")
    assert definition is not None
    assert definition.name == "MyFunctionalTool"
    assert "simple functional tool" in definition.description
    assert definition.tool_class is None
    assert callable(definition.custom_factory)

    # 2. Create a new instance using the registry.
    instance_from_registry = default_tool_registry.create_tool("MyFunctionalTool")

    # 3. Verify the new instance.
    assert isinstance(instance_from_registry, FunctionalTool)
    assert instance_from_registry is not dummy_func

    # 4. Verify the new instance works correctly.
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-123"
    result = await instance_from_registry.execute(context=mock_context, text="hello")
    assert result == "processed: hello"

@pytest.mark.asyncio
async def test_create_stateful_functional_tool_from_registry():
    """Tests creating and using a stateful functional tool via the registry."""
    # Define the tool inside the test to avoid import-time registration
    @tool(name="StatefulCounter")
    def stateful_func(tool_state: Dict[str, Any]) -> int:
        """My stateful counter."""
        count = tool_state.get('count', 10)
        count += 1
        tool_state['count'] = count
        return count

    # Create the tool instance from the registry
    counter_tool_instance = default_tool_registry.create_tool("StatefulCounter")
    assert isinstance(counter_tool_instance, FunctionalTool)
    assert counter_tool_instance.tool_state == {}

    mock_context = MagicMock()
    mock_context.agent_id = "stateful-agent"

    # Execute multiple times and check if state persists
    result1 = await counter_tool_instance.execute(context=mock_context)
    assert result1 == 11
    assert counter_tool_instance.tool_state['count'] == 11

    result2 = await counter_tool_instance.execute(context=mock_context)
    assert result2 == 12
    assert counter_tool_instance.tool_state['count'] == 12

def test_create_tool_not_found_raises_error():
    """Tests that creating an unregistered tool raises ValueError."""
    with pytest.raises(ValueError, match="No tool definition found for name 'NonExistentTool'"):
        default_tool_registry.create_tool("NonExistentTool")

def test_create_tool_instantiation_fails_raises_error():
    """Tests that a tool instantiation failure is handled correctly."""
    fail_def = ToolDefinition(
        name="DummyToolFailsInit",
        description="...",
        argument_schema_provider=lambda: None,
        config_schema_provider=lambda: None,
        tool_class=DummyToolFailsInit,
        origin=ToolOrigin.LOCAL,
        category=ToolCategory.GENERAL
    )
    default_tool_registry.register_tool(fail_def)
    
    with pytest.raises(TypeError, match="Failed to create tool 'DummyToolFailsInit': Initialization failed"):
        default_tool_registry.create_tool("DummyToolFailsInit")

def test_register_invalid_definition_raises_error():
    """Tests that registering a non-ToolDefinition object raises ValueError."""
    with pytest.raises(ValueError, match="Attempted to register an object that is not a ToolDefinition"):
        default_tool_registry.register_tool("not a definition") # type: ignore
