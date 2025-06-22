# file: autobyteus/tests/unit_tests/tools/registry/test_tool_registry.py
import pytest
from typing import Optional, Any
from unittest.mock import MagicMock

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.functional_tool import tool, FunctionalTool
from autobyteus.tools.parameter_schema import ParameterSchema
from autobyteus.tools.registry import ToolRegistry, ToolDefinition
from autobyteus.tools.tool_config import ToolConfig

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

def dummy_factory(config: Optional[ToolConfig] = None) -> DummyFactoryTool:
    """Factory function for creating DummyFactoryTool."""
    source = "factory_default"
    if config and config.get("source_override"):
        source = config.get("source_override")
    # The factory must now also pass the config to the tool's constructor
    return DummyFactoryTool(source=source, config=config)

# --- Pytest Fixtures ---

@pytest.fixture
def clean_registry(monkeypatch):
    """Provides a clean ToolRegistry instance for each test."""
    registry = ToolRegistry()
    original_defs = registry._definitions.copy()
    registry._definitions.clear()
    yield registry
    registry._definitions = original_defs


@pytest.fixture
def no_config_def() -> ToolDefinition:
    """Fixture for DummyToolNoConfig's definition."""
    return ToolDefinition(
        name="DummyToolNoConfig",
        description="A dummy tool without config.",
        argument_schema=None,
        tool_class=DummyToolNoConfig
    )

@pytest.fixture
def with_config_def() -> ToolDefinition:
    """Fixture for DummyToolWithConfig's definition."""
    return ToolDefinition(
        name="DummyToolWithConfig",
        description="A dummy tool with config.",
        argument_schema=None,
        tool_class=DummyToolWithConfig
    )

@pytest.fixture
def factory_def() -> ToolDefinition:
    """Fixture for the factory-based tool's definition."""
    return ToolDefinition(
        name="DummyFactoryTool",
        description="A dummy tool created by a factory.",
        argument_schema=None,
        custom_factory=dummy_factory
    )

# --- Test Cases ---

def test_singleton_instance():
    """Tests that ToolRegistry is a singleton."""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()
    assert registry1 is registry2

def test_register_and_get_tool_definition(clean_registry: ToolRegistry, no_config_def: ToolDefinition):
    """Tests registering a tool and retrieving its definition."""
    assert clean_registry.get_tool_definition("DummyToolNoConfig") is None
    clean_registry.register_tool(no_config_def)
    retrieved_def = clean_registry.get_tool_definition("DummyToolNoConfig")
    assert retrieved_def is no_config_def
    assert retrieved_def.name == "DummyToolNoConfig"

def test_register_overwrites_existing(clean_registry: ToolRegistry, no_config_def: ToolDefinition):
    """Tests that registering a tool with an existing name overwrites the old one."""
    clean_registry.register_tool(no_config_def)
    
    new_def = ToolDefinition(
        name="DummyToolNoConfig", # Same name
        description="An updated description.",
        argument_schema=None,
        tool_class=DummyToolNoConfig
    )
    clean_registry.register_tool(new_def)
    
    retrieved_def = clean_registry.get_tool_definition("DummyToolNoConfig")
    assert retrieved_def is not no_config_def
    assert retrieved_def.description == "An updated description."

def test_list_tools(clean_registry: ToolRegistry, no_config_def: ToolDefinition, factory_def: ToolDefinition):
    """Tests listing registered tools."""
    assert clean_registry.list_tools() == []
    assert clean_registry.list_tool_names() == []
    
    clean_registry.register_tool(no_config_def)
    clean_registry.register_tool(factory_def)
    
    defs = clean_registry.list_tools()
    names = clean_registry.list_tool_names()
    
    assert len(defs) == 2
    assert len(names) == 2
    assert "DummyToolNoConfig" in names
    assert "DummyFactoryTool" in names

def test_create_simple_class_based_tool(clean_registry: ToolRegistry, no_config_def: ToolDefinition):
    """Tests creating a simple tool from its class without config."""
    clean_registry.register_tool(no_config_def)
    tool_instance = clean_registry.create_tool("DummyToolNoConfig")
    
    assert isinstance(tool_instance, DummyToolNoConfig)
    assert tool_instance.config_received is None

@pytest.mark.asyncio
async def test_create_class_based_tool_with_config(clean_registry: ToolRegistry, with_config_def: ToolDefinition):
    """Tests creating a class-based tool, passing a ToolConfig."""
    clean_registry.register_tool(with_config_def)
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-for-config-tool"
    
    # Create without config
    tool_instance_default = clean_registry.create_tool("DummyToolWithConfig")
    assert isinstance(tool_instance_default, DummyToolWithConfig)
    assert await tool_instance_default.execute(mock_context) == "default"

    # Create with config
    config = ToolConfig(params={"value": "custom_value"})
    tool_instance_custom = clean_registry.create_tool("DummyToolWithConfig", config=config)
    assert isinstance(tool_instance_custom, DummyToolWithConfig)
    assert await tool_instance_custom.execute(mock_context) == "custom_value"

@pytest.mark.asyncio
async def test_create_factory_based_tool(clean_registry: ToolRegistry, factory_def: ToolDefinition):
    """Tests creating a tool using a custom factory."""
    clean_registry.register_tool(factory_def)
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-for-factory-tool"

    # Create without config
    tool_instance_default = clean_registry.create_tool("DummyFactoryTool")
    assert isinstance(tool_instance_default, DummyFactoryTool)
    assert await tool_instance_default.execute(mock_context) == "created from factory_default"
    assert tool_instance_default._config is None

    # Create with config passed to factory
    config = ToolConfig(params={"source_override": "factory_custom"})
    tool_instance_custom = clean_registry.create_tool("DummyFactoryTool", config=config)
    assert isinstance(tool_instance_custom, DummyFactoryTool)
    assert await tool_instance_custom.execute(mock_context) == "created from factory_custom"
    assert tool_instance_custom._config == config

@pytest.mark.asyncio
async def test_create_functional_tool_from_registry(clean_registry: ToolRegistry):
    """Tests creating a functional tool instance from the registry after the refactor."""
    @tool(name="MyFunctionalTool")
    async def dummy_func(context: Any, text: str) -> str:
        """A simple functional tool for testing."""
        return f"processed: {text}"
    
    # 1. Verify it was registered with the correct definition type
    definition = clean_registry.get_tool_definition("MyFunctionalTool")
    assert definition is not None
    assert definition.name == "MyFunctionalTool"
    assert "simple functional tool" in definition.description
    assert definition.tool_class is None
    assert callable(definition.custom_factory)

    # 2. Create a new instance using the registry.
    instance_from_registry = clean_registry.create_tool("MyFunctionalTool")

    # 3. Verify the new instance.
    assert isinstance(instance_from_registry, FunctionalTool)
    assert instance_from_registry is not dummy_func

    # 4. Verify the new instance works correctly.
    mock_context = MagicMock()
    mock_context.agent_id = "test-agent-123"
    result = await instance_from_registry.execute(context=mock_context, text="hello")
    assert result == "processed: hello"


def test_create_tool_not_found_raises_error(clean_registry: ToolRegistry):
    """Tests that creating an unregistered tool raises ValueError."""
    with pytest.raises(ValueError, match="No tool definition found for name 'NonExistentTool'"):
        clean_registry.create_tool("NonExistentTool")

def test_create_tool_instantiation_fails_raises_error(clean_registry: ToolRegistry):
    """Tests that a tool instantiation failure is handled correctly."""
    fail_def = ToolDefinition(
        name="DummyToolFailsInit",
        description="...",
        argument_schema=None,
        tool_class=DummyToolFailsInit
    )
    clean_registry.register_tool(fail_def)
    
    with pytest.raises(TypeError, match="Failed to create tool 'DummyToolFailsInit': Initialization failed"):
        clean_registry.create_tool("DummyToolFailsInit")

def test_register_invalid_definition_raises_error(clean_registry: ToolRegistry):
    """Tests that registering a non-ToolDefinition object raises ValueError."""
    with pytest.raises(ValueError, match="Attempted to register an object that is not a ToolDefinition"):
        clean_registry.register_tool("not a definition") # type: ignore
