# file: autobyteus/tests/unit_tests/agent/factory/test_agent_factory.py
import pytest
from unittest.mock import MagicMock, patch, ANY
from typing import Any

from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.context.agent_runtime_state import AgentRuntimeState
from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.agent import Agent
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.tools.base_tool import BaseTool
from autobyteus.agent.handlers import EventHandlerRegistry, UserInputMessageEventHandler, LifecycleEventLogger
from autobyteus.agent.events import UserMessageReceivedEvent, AgentReadyEvent, AgentErrorEvent, AgentStoppedEvent

@pytest.fixture
def agent_factory():
    """Provides a clean instance of the AgentFactory for each test."""
    # Reset singleton instance for test isolation
    if hasattr(AgentFactory, '_instance'):
        AgentFactory._instance = None
    return AgentFactory()

@pytest.fixture
def mock_llm_for_factory():
    return MagicMock(spec=BaseLLM)

@pytest.fixture
def mock_tool_for_factory():
    tool = MagicMock(spec=BaseTool)
    tool.get_name.return_value = "factory_tool"
    return tool

@pytest.fixture
def valid_agent_config(mock_llm_for_factory, mock_tool_for_factory):
    """Provides a valid AgentConfig for factory tests."""
    return AgentConfig(
        name="FactoryTestAgent",
        role="factory-tester",
        description="Test agent for factory",
        llm_instance=mock_llm_for_factory,
        system_prompt="System prompt",
        tools=[mock_tool_for_factory]
    )


def test_factory_initialization(agent_factory: AgentFactory):
    """Tests the factory initializes correctly (no more dependencies)."""
    assert isinstance(agent_factory, AgentFactory)
    assert not hasattr(agent_factory, 'llm_factory') # Dependency removed
    assert not hasattr(agent_factory, 'tool_registry') # Dependency removed

def test_get_default_event_handler_registry(agent_factory: AgentFactory):
    """Tests that the factory creates a correct registry of event handlers."""
    registry = agent_factory._get_default_event_handler_registry()
    assert isinstance(registry, EventHandlerRegistry)
    
    # Check for a representative handler
    assert isinstance(registry.get_handler(UserMessageReceivedEvent), UserInputMessageEventHandler)

    # Check that lifecycle events are handled by the same logger instance
    lifecycle_logger_instance = registry.get_handler(AgentReadyEvent) 
    assert isinstance(lifecycle_logger_instance, LifecycleEventLogger)
    assert registry.get_handler(AgentStoppedEvent) is lifecycle_logger_instance
    assert registry.get_handler(AgentErrorEvent) is lifecycle_logger_instance

    # Bootstrap events are registered by default.


def test_create_agent_success(agent_factory: AgentFactory, valid_agent_config: AgentConfig):
    """Tests the successful creation of an Agent."""

    # Create a mock instance of AgentRuntime. This is what _create_runtime_with_id should return.
    mock_runtime_instance = MagicMock(spec=AgentRuntime)
    # FIX: Explicitly create the 'context' attribute on the mock, so we can set its 'agent_id'.
    mock_runtime_instance.context = MagicMock()

    # Define a side_effect function for our mock. This function will be called
    # instead of the real _create_runtime_with_id. It allows us to capture the randomly
    # generated agent_id and attach it to our mock_runtime_instance.
    def mock_create_runtime_side_effect(agent_id: str, config: AgentConfig):
        # The Agent constructor reads the agent_id from runtime.context.agent_id.
        # We set it here so the created Agent object has the correct ID.
        mock_runtime_instance.context.agent_id = agent_id
        return mock_runtime_instance

    with patch.object(agent_factory, '_create_runtime_with_id', side_effect=mock_create_runtime_side_effect) as mock_create_runtime:
        agent = agent_factory.create_agent(config=valid_agent_config)

        assert isinstance(agent, Agent)
        assert agent.agent_id.startswith(f"{valid_agent_config.name}_{valid_agent_config.role}")
        
        # Verify that _create_runtime_with_id was called correctly with the agent_id that the agent ended up with
        mock_create_runtime.assert_called_once_with(
            agent_id=agent.agent_id, 
            config=valid_agent_config,
        )
        
        # Verify the agent is stored in the factory under the correct ID
        assert agent_factory.get_agent(agent.agent_id) is agent
        assert agent.agent_id in agent_factory.list_active_agent_ids()

def test_create_agent_invalid_config(agent_factory: AgentFactory):
    """Tests that create_agent raises TypeError for invalid config."""
    with pytest.raises(TypeError, match="Expected AgentConfig instance"):
        agent_factory.create_agent(config="not a config")


def test_restore_agent_uses_existing_id(agent_factory: AgentFactory, valid_agent_config: AgentConfig):
    mock_runtime_instance = MagicMock(spec=AgentRuntime)
    mock_runtime_instance.context = MagicMock()

    def mock_create_runtime_side_effect(agent_id: str, config: AgentConfig, memory_dir_override=None, restore_options=None):
        mock_runtime_instance.context.agent_id = agent_id
        return mock_runtime_instance

    with patch.object(agent_factory, '_create_runtime_with_id', side_effect=mock_create_runtime_side_effect) as mock_create_runtime:
        agent = agent_factory.restore_agent(agent_id="restored_agent", config=valid_agent_config, memory_dir="/tmp/memory")

        assert isinstance(agent, Agent)
        assert agent.agent_id == "restored_agent"
        mock_create_runtime.assert_called_once()
        _, kwargs = mock_create_runtime.call_args
        assert kwargs["memory_dir_override"] == "/tmp/memory"
        assert kwargs["restore_options"] is not None

def test_prepare_tool_instances(agent_factory: AgentFactory, mock_tool_for_factory):
    """Tests the internal logic for preparing the tool instance dictionary."""
    config = MagicMock(spec=AgentConfig)
    config.tools = [mock_tool_for_factory]
    
    tool_dict = agent_factory._prepare_tool_instances("test_id", config)
    
    assert "factory_tool" in tool_dict
    assert tool_dict["factory_tool"] is mock_tool_for_factory

def test_prepare_tool_instances_duplicate_names(agent_factory: AgentFactory, caplog):
    """Tests that a warning is logged for duplicate tool names."""
    tool1 = MagicMock(spec=BaseTool); tool1.get_name.return_value = "duplicate_tool"
    tool2 = MagicMock(spec=BaseTool); tool2.get_name.return_value = "duplicate_tool"
    config = MagicMock(spec=AgentConfig)
    config.tools = [tool1, tool2]
    
    tool_dict = agent_factory._prepare_tool_instances("test_id", config)

    assert "Duplicate tool name 'duplicate_tool' encountered" in caplog.text
    assert tool_dict["duplicate_tool"] is tool2 # The last one wins

# Re-ordered decorators for clarity and corrected the patch target for AgentRuntime
@patch('autobyteus.agent.runtime.agent_runtime.AgentRuntime', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentContext', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentRuntimeState', autospec=True)
def test_create_runtime_populates_state(MockAgentRuntimeState, MockAgentContext, MockAgentRuntime, agent_factory: AgentFactory, valid_agent_config: AgentConfig):
    """
    Tests that _create_runtime correctly populates the runtime state with
    the LLM and tool instances from the config.
    """
    mock_state_instance = MockAgentRuntimeState.return_value
    
    # We call the real _create_runtime_with_id method. The decorators will intercept the
    # creation of AgentRuntimeState, AgentContext, and AgentRuntime.
    runtime = agent_factory._create_runtime_with_id(
        agent_id="test-runtime-agent",
        config=valid_agent_config,
    )

    # Check that the mock AgentRuntime constructor was called with the correct context.
    MockAgentRuntime.assert_called_once_with(
        context=MockAgentContext.return_value,
        event_handler_registry=ANY
    )
    
    # Check that the state instance was populated BEFORE being passed to AgentContext
    assert mock_state_instance.llm_instance == valid_agent_config.llm_instance
    
    tool_name = valid_agent_config.tools[0].get_name()
    assert tool_name in mock_state_instance.tool_instances
    assert mock_state_instance.tool_instances[tool_name] is valid_agent_config.tools[0]
    
    # Verify AgentContext was created with the populated state
    MockAgentContext.assert_called_once_with(
        agent_id="test-runtime-agent",
        config=valid_agent_config,
        state=mock_state_instance
    )
