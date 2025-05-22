# file: autobyteus/tests/unit_tests/agent/factory/test_agent_factory.py
import pytest
from unittest.mock import MagicMock, patch, ANY

from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.context import AgentContext
from autobyteus.agent.events import AgentEventQueues, UserMessageReceivedEvent, LifecycleEvent
from autobyteus.agent.handlers import EventHandlerRegistry, UserInputMessageEventHandler, LifecycleEventLogger
from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel, LLMConfig
from autobyteus.tools.registry import ToolRegistry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.agent.events import AgentStartedEvent # For checking lifecycle logger registration

@pytest.fixture
def mock_tool_registry():
    return MagicMock(spec=ToolRegistry)

@pytest.fixture
def mock_llm_factory():
    factory = MagicMock(spec=LLMFactory)
    factory.create_llm = MagicMock(return_value=MagicMock(spec=BaseLLM))
    return factory

@pytest.fixture
def agent_factory_instance(mock_tool_registry, mock_llm_factory):
    return AgentFactory(tool_registry=mock_tool_registry, llm_factory=mock_llm_factory)

@pytest.fixture
def sample_agent_definition():
    return AgentDefinition(
        name="SampleAgent",
        role="tester",
        description="A sample agent for testing.",
        system_prompt="You are a helpful testing assistant.",
        tool_names=["tool1", "tool2"],
        input_processor_names=["PassthroughInputProcessor"],
        llm_response_processor_names=["xml_tool_usage"]
    )

@pytest.fixture
def sample_llm_model():
    model = LLMModel.MISTRAL_LARGE_API 
    model.default_config = LLMConfig(temperature=0.7) 
    return model


# Refactored tests to be function-based

def test_initialization(agent_factory_instance: AgentFactory, mock_tool_registry, mock_llm_factory):
    assert agent_factory_instance.tool_registry == mock_tool_registry
    assert agent_factory_instance.llm_factory == mock_llm_factory

def test_initialization_type_errors():
    with pytest.raises(TypeError, match="must be an instance of ToolRegistry"):
        AgentFactory(tool_registry="not a registry", llm_factory=MagicMock(spec=LLMFactory))
    with pytest.raises(TypeError, match="must be an instance of LLMFactory"):
        AgentFactory(tool_registry=MagicMock(spec=ToolRegistry), llm_factory="not a factory")

def test_get_default_event_handler_registry(agent_factory_instance: AgentFactory):
    registry = agent_factory_instance._get_default_event_handler_registry()
    assert isinstance(registry, EventHandlerRegistry)
    assert registry.get_handler(UserMessageReceivedEvent) is not None
    assert isinstance(registry.get_handler(UserMessageReceivedEvent), UserInputMessageEventHandler)
    
    lifecycle_logger_instance_type = type(registry.get_handler(AgentStartedEvent))
    assert lifecycle_logger_instance_type is LifecycleEventLogger

@patch('autobyteus.agent.factory.agent_factory.AgentContext', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentEventQueues', autospec=True)
def test_create_agent_context_successful(MockAgentEventQueues, MockAgentContext,
                                       agent_factory_instance: AgentFactory,
                                       sample_agent_definition: AgentDefinition,
                                       sample_llm_model: LLMModel,
                                       mock_tool_registry: ToolRegistry,
                                       mock_llm_factory: LLMFactory):
    
    mock_tool_instance = MagicMock(spec=BaseTool)
    mock_tool_registry.create_tool.return_value = mock_tool_instance
    
    mock_llm_instance = MagicMock(spec=BaseLLM)
    mock_llm_factory.create_llm.return_value = mock_llm_instance

    mock_workspace = MagicMock(spec=BaseAgentWorkspace)
    llm_config_override = {"max_tokens": 1000}
    
    # Corrected ToolConfig instantiation based on deduction from errors
    tool_config_data_dict = {"key": "value"}
    # Assuming ToolConfig takes a dictionary as its first positional argument
    tool_config_override = {"tool1": ToolConfig(tool_config_data_dict)} 
    auto_execute_tools_override = False

    context = agent_factory_instance.create_agent_context(
        agent_id="test_ctx_id_1",
        definition=sample_agent_definition,
        llm_model=sample_llm_model,
        workspace=mock_workspace,
        llm_config_override=llm_config_override,
        tool_config_override=tool_config_override,
        auto_execute_tools_override=auto_execute_tools_override
    )

    assert mock_tool_registry.create_tool.call_count == len(sample_agent_definition.tool_names)
    mock_tool_registry.create_tool.assert_any_call("tool1", tool_config_override["tool1"])
    mock_tool_registry.create_tool.assert_any_call("tool2", None)

    mock_llm_factory.create_llm.assert_called_once()
    called_llm_config: LLMConfig = mock_llm_factory.create_llm.call_args[1]['custom_config']
    assert called_llm_config.system_message == sample_agent_definition.system_prompt
    assert called_llm_config.max_tokens == 1000 
    assert called_llm_config.temperature == sample_llm_model.default_config.temperature


    MockAgentEventQueues.assert_called_once()
    
    MockAgentContext.assert_called_once_with(
        agent_id="test_ctx_id_1",
        definition=sample_agent_definition,
        queues=ANY, 
        llm_instance=mock_llm_instance,
        tool_instances={"tool1": mock_tool_instance, "tool2": mock_tool_instance},
        workspace=mock_workspace,
        auto_execute_tools=auto_execute_tools_override
    )
    assert context == MockAgentContext.return_value

def test_create_agent_context_invalid_inputs(agent_factory_instance: AgentFactory, sample_llm_model: LLMModel):
    with pytest.raises(TypeError, match="Expected AgentDefinition"):
        agent_factory_instance.create_agent_context("id", "not a definition", sample_llm_model)
    
    with pytest.raises(TypeError, match="An 'llm_model' of type LLMModel must be specified"):
        agent_factory_instance.create_agent_context("id", MagicMock(spec=AgentDefinition), "not an llm model")

    with pytest.raises(TypeError, match="Expected BaseAgentWorkspace or None"):
        agent_factory_instance.create_agent_context(
            "id", MagicMock(spec=AgentDefinition), sample_llm_model, workspace="not a workspace")


def test_create_agent_context_tool_creation_failure(agent_factory_instance: AgentFactory,
                                                   sample_agent_definition: AgentDefinition,
                                                   sample_llm_model: LLMModel,
                                                   mock_tool_registry: ToolRegistry):
    mock_tool_registry.create_tool.side_effect = ValueError("Tool creation failed")
    with pytest.raises(ValueError, match="Failed to create tools"):
        agent_factory_instance.create_agent_context(
            "id", sample_agent_definition, sample_llm_model)

def test_create_agent_context_llm_creation_failure(agent_factory_instance: AgentFactory,
                                                  sample_agent_definition: AgentDefinition,
                                                  sample_llm_model: LLMModel,
                                                  mock_llm_factory: LLMFactory):
    mock_llm_factory.create_llm.side_effect = ValueError("LLM creation failed")
    with pytest.raises(ValueError, match="Failed to create LLM"):
        agent_factory_instance.create_agent_context(
            "id", sample_agent_definition, sample_llm_model)


@patch('autobyteus.agent.factory.agent_factory.AgentRuntime', autospec=True)
def test_create_agent_runtime(MockAgentRuntime, agent_factory_instance: AgentFactory,
                              sample_agent_definition: AgentDefinition,
                              sample_llm_model: LLMModel):
    
    mock_created_context = MagicMock(spec=AgentContext)
    agent_factory_instance.create_agent_context = MagicMock(return_value=mock_created_context)
    
    mock_event_registry = MagicMock(spec=EventHandlerRegistry)
    agent_factory_instance._get_default_event_handler_registry = MagicMock(return_value=mock_event_registry)

    runtime = agent_factory_instance.create_agent_runtime(
        agent_id="test_rt_id_1",
        definition=sample_agent_definition,
        llm_model=sample_llm_model
    )

    agent_factory_instance.create_agent_context.assert_called_once_with(
        "test_rt_id_1", sample_agent_definition,
        llm_model=sample_llm_model,
        workspace=None,
        llm_config_override=None,
        tool_config_override=None,
        auto_execute_tools_override=True
    )
    agent_factory_instance._get_default_event_handler_registry.assert_called_once()
    MockAgentRuntime.assert_called_once_with(context=mock_created_context, event_handler_registry=mock_event_registry)
    assert runtime == MockAgentRuntime.return_value
