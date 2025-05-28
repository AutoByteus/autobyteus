# file: autobyteus/tests/unit_tests/agent/factory/test_agent_factory.py
import pytest
from unittest.mock import MagicMock, patch, ANY

from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.context import AgentConfig, AgentRuntimeState, AgentContext
from autobyteus.agent.events import (
    AgentEventQueues, UserMessageReceivedEvent, LifecycleEvent, AgentStartedEvent, AgentStoppedEvent, AgentErrorEvent,
    CreateToolInstancesEvent, ProcessSystemPromptEvent, FinalizeLLMConfigEvent, CreateLLMInstanceEvent,
    InterAgentMessageReceivedEvent, LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent,
    ToolResultEvent, GenericEvent, ToolExecutionApprovalEvent, LLMUserMessageReadyEvent, ApprovedToolInvocationEvent
)
from autobyteus.agent.handlers import (
    EventHandlerRegistry, UserInputMessageEventHandler, LifecycleEventLogger,
    CreateToolInstancesEventHandler, ProcessSystemPromptEventHandler, FinalizeLLMConfigEventHandler, CreateLLMInstanceEventHandler,
    InterAgentMessageReceivedEventHandler, LLMCompleteResponseReceivedEventHandler, ToolInvocationRequestEventHandler,
    ToolResultEventHandler, GenericEventHandler, ToolExecutionApprovalEventHandler, LLMUserMessageReadyEventHandler,
    ApprovedToolInvocationEventHandler
)
from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig 
from autobyteus.tools.registry import ToolRegistry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry

@pytest.fixture
def mock_tool_registry():
    return MagicMock(spec=ToolRegistry)

@pytest.fixture
def mock_llm_factory():
    factory = MagicMock(spec=LLMFactory)
    factory.create_llm = MagicMock(return_value=MagicMock(spec=BaseLLM))
    return factory

@pytest.fixture
def mock_system_prompt_processor_registry():
    return MagicMock(spec=SystemPromptProcessorRegistry)

@pytest.fixture
def agent_factory_instance(mock_tool_registry, mock_llm_factory, mock_system_prompt_processor_registry):
    return AgentFactory(
        tool_registry=mock_tool_registry,
        llm_factory=mock_llm_factory,
        system_prompt_processor_registry=mock_system_prompt_processor_registry
    )

@pytest.fixture
def sample_agent_definition():
    # This will now default use_xml_tool_format=True
    return AgentDefinition(
        name="SampleAgent",
        role="tester",
        description="A sample agent for testing.",
        system_prompt="You are a helpful testing assistant. {{tools}} {{tool_examples}}",
        tool_names=["tool1", "tool2"],
        input_processor_names=["PassthroughInputProcessor"],
        llm_response_processor_names=["xml_tool_usage", "json_tool_usage"],
        system_prompt_processor_names=["ToolDescriptionInjector", "ToolUsageExampleInjector"]
        # use_xml_tool_format defaults to True
    )

@pytest.fixture
def sample_agent_definition_json_format():
    # Specific definition for JSON format testing
    return AgentDefinition(
        name="SampleAgentJson",
        role="testerJson",
        description="A sample agent for testing JSON format.",
        system_prompt="You are a helpful testing assistant (JSON). {{tools}} {{tool_examples}}",
        tool_names=["tool_json1", "tool_json2"],
        use_xml_tool_format=False # Explicitly set to False
    )


@pytest.fixture
def sample_llm_model_name() -> str:
    return "TEST_LLM_MODEL_XYZ_V1" 

def test_initialization(agent_factory_instance: AgentFactory, mock_tool_registry, mock_llm_factory, mock_system_prompt_processor_registry):
    assert agent_factory_instance.tool_registry == mock_tool_registry
    assert agent_factory_instance.llm_factory == mock_llm_factory
    assert agent_factory_instance.system_prompt_processor_registry == mock_system_prompt_processor_registry

def test_initialization_type_errors():
    with pytest.raises(TypeError, match="must be an instance of ToolRegistry"):
        AgentFactory(tool_registry="not a registry", llm_factory=MagicMock(spec=LLMFactory), system_prompt_processor_registry=MagicMock(spec=SystemPromptProcessorRegistry))
    with pytest.raises(TypeError, match="must be an instance of LLMFactory"):
        AgentFactory(tool_registry=MagicMock(spec=ToolRegistry), llm_factory="not a factory", system_prompt_processor_registry=MagicMock(spec=SystemPromptProcessorRegistry))

def test_get_default_event_handler_registry(agent_factory_instance: AgentFactory):
    registry = agent_factory_instance._get_default_event_handler_registry()
    assert isinstance(registry, EventHandlerRegistry)
    assert isinstance(registry.get_handler(CreateToolInstancesEvent), CreateToolInstancesEventHandler)
    assert isinstance(registry.get_handler(ProcessSystemPromptEvent), ProcessSystemPromptEventHandler)
    assert isinstance(registry.get_handler(FinalizeLLMConfigEvent), FinalizeLLMConfigEventHandler)
    assert isinstance(registry.get_handler(CreateLLMInstanceEvent), CreateLLMInstanceEventHandler)
    assert isinstance(registry.get_handler(UserMessageReceivedEvent), UserInputMessageEventHandler)
    assert isinstance(registry.get_handler(InterAgentMessageReceivedEvent), InterAgentMessageReceivedEventHandler)
    assert isinstance(registry.get_handler(LLMCompleteResponseReceivedEvent), LLMCompleteResponseReceivedEventHandler)
    assert isinstance(registry.get_handler(PendingToolInvocationEvent), ToolInvocationRequestEventHandler)
    assert isinstance(registry.get_handler(ToolResultEvent), ToolResultEventHandler)
    assert isinstance(registry.get_handler(GenericEvent), GenericEventHandler)
    assert isinstance(registry.get_handler(ToolExecutionApprovalEvent), ToolExecutionApprovalEventHandler)
    assert isinstance(registry.get_handler(LLMUserMessageReadyEvent), LLMUserMessageReadyEventHandler)
    assert isinstance(registry.get_handler(ApprovedToolInvocationEvent), ApprovedToolInvocationEventHandler)
    lifecycle_logger_instance = registry.get_handler(AgentStartedEvent)
    assert isinstance(lifecycle_logger_instance, LifecycleEventLogger)
    assert registry.get_handler(AgentStoppedEvent) == lifecycle_logger_instance
    assert registry.get_handler(AgentErrorEvent) == lifecycle_logger_instance


@patch('autobyteus.agent.factory.agent_factory.AgentConfig', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentRuntimeState', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentEventQueues', autospec=True)
def test_create_agent_config_and_state_successful(
    MockAgentEventQueues, MockAgentRuntimeState, MockAgentConfig,
    agent_factory_instance: AgentFactory,
    sample_agent_definition: AgentDefinition, # This fixture uses default use_xml_tool_format=True
    sample_llm_model_name: str):

    mock_workspace = MagicMock(spec=BaseAgentWorkspace)
    custom_llm_config_obj = LLMConfig(temperature=0.8)
    tool_config_data_dict = {"tool_specific_key": "tool_specific_value"}
    custom_tool_config_obj = {"tool1": ToolConfig(tool_config_data_dict)} 
    auto_execute_setting = False

    created_config, created_state = agent_factory_instance._create_agent_config_and_state(
        agent_id="test_agent_id_001",
        definition=sample_agent_definition, # sample_agent_definition implicitly has use_xml_tool_format=True
        llm_model_name=sample_llm_model_name,
        workspace=mock_workspace,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )

    MockAgentConfig.assert_called_once_with(
        agent_id="test_agent_id_001",
        definition=sample_agent_definition, # definition itself carries use_xml_tool_format
        auto_execute_tools=auto_execute_setting,
        llm_model_name=sample_llm_model_name,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj
    )
    assert created_config == MockAgentConfig.return_value
    MockAgentEventQueues.assert_called_once()
    MockAgentRuntimeState.assert_called_once_with(
        agent_id="test_agent_id_001",
        queues=MockAgentEventQueues.return_value,
        workspace=mock_workspace
    )
    assert created_state == MockAgentRuntimeState.return_value


@patch('autobyteus.agent.factory.agent_factory.AgentContext', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentConfig') 
@patch('autobyteus.agent.factory.agent_factory.AgentRuntimeState') 
def test_create_agent_context_successful(
    MockAgentRuntimeState, MockAgentConfig, MockAgentContextCls,
    agent_factory_instance: AgentFactory,
    sample_agent_definition: AgentDefinition, # This fixture uses default use_xml_tool_format=True
    sample_llm_model_name: str):

    mock_workspace = MagicMock(spec=BaseAgentWorkspace)
    custom_llm_config_obj = LLMConfig(temperature=0.8)
    custom_tool_config_obj = {"tool1": ToolConfig({"key": "value"})}
    auto_execute_setting = False

    mock_created_config_instance = MockAgentConfig.return_value
    mock_created_state_instance = MockAgentRuntimeState.return_value
    
    with patch.object(agent_factory_instance, '_create_agent_config_and_state', return_value=(mock_created_config_instance, mock_created_state_instance)) as mock_create_config_state:
        context = agent_factory_instance.create_agent_context(
            agent_id="test_ctx_id_1",
            definition=sample_agent_definition, # sample_agent_definition implicitly has use_xml_tool_format=True
            llm_model_name=sample_llm_model_name,
            workspace=mock_workspace,
            custom_llm_config=custom_llm_config_obj,
            custom_tool_config=custom_tool_config_obj,
            auto_execute_tools=auto_execute_setting
        )

        mock_create_config_state.assert_called_once_with(
            agent_id="test_ctx_id_1",
            definition=sample_agent_definition, # definition itself carries use_xml_tool_format
            llm_model_name=sample_llm_model_name,
            workspace=mock_workspace,
            custom_llm_config=custom_llm_config_obj,
            custom_tool_config=custom_tool_config_obj,
            auto_execute_tools=auto_execute_setting
        )
        MockAgentContextCls.assert_called_once_with(
            config=mock_created_config_instance,
            state=mock_created_state_instance
        )
        assert context == MockAgentContextCls.return_value

def test_create_agent_context_invalid_inputs(agent_factory_instance: AgentFactory, sample_llm_model_name: str):
    sample_def = MagicMock(spec=AgentDefinition)
    # Add use_xml_tool_format to the spec if validation in AgentConfig relies on it being present
    sample_def.use_xml_tool_format = True 
    
    with pytest.raises(TypeError, match="Expected AgentDefinition"):
        agent_factory_instance.create_agent_context("id", "not a definition", sample_llm_model_name)
    with pytest.raises(TypeError, match="An 'llm_model_name' .* must be specified"):
        agent_factory_instance.create_agent_context("id", sample_def, llm_model_name=None) # type: ignore
    with pytest.raises(TypeError, match="An 'llm_model_name' .* must be specified"):
        agent_factory_instance.create_agent_context("id", sample_def, llm_model_name=123) # type: ignore
    with pytest.raises(TypeError, match="Expected BaseAgentWorkspace or None"):
        agent_factory_instance.create_agent_context(
            "id", sample_def, sample_llm_model_name, workspace="not a workspace")
    with pytest.raises(TypeError, match="custom_llm_config must be an LLMConfig instance or None"):
        agent_factory_instance.create_agent_context(
            "id", sample_def, sample_llm_model_name, custom_llm_config={"temp": 0.5}) # type: ignore
    with pytest.raises(TypeError, match="custom_tool_config must be a Dict\\[str, ToolConfig\\] or None"):
        agent_factory_instance.create_agent_context(
            "id", sample_def, sample_llm_model_name, custom_tool_config={"tool1": {"cfg": "val"}}) # type: ignore
            
    # This specific check is inside AgentConfig's __init__
    with pytest.raises(TypeError, match="AgentConfig 'custom_tool_config' must be a Dict\\[str, ToolConfig\\] or None."):
         with patch('autobyteus.agent.factory.agent_factory.AgentEventQueues', autospec=True): 
            agent_factory_instance.create_agent_context(
                "id", sample_def, sample_llm_model_name, 
                custom_tool_config={"tool1": "not_a_tool_config_object"} # type: ignore
            )


@patch('autobyteus.agent.factory.agent_factory.AgentRuntime', autospec=True)
def test_create_agent_runtime(MockAgentRuntimeCls, agent_factory_instance: AgentFactory,
                              sample_agent_definition: AgentDefinition, # This fixture uses default use_xml_tool_format=True
                              sample_llm_model_name: str):
    mock_created_context = MagicMock(spec=AgentContext)
    agent_factory_instance.create_agent_context = MagicMock(return_value=mock_created_context)
    mock_event_registry = MagicMock(spec=EventHandlerRegistry)
    agent_factory_instance._get_default_event_handler_registry = MagicMock(return_value=mock_event_registry)

    custom_llm_config_obj = LLMConfig(temperature=0.1)
    custom_tool_config_obj = {"tool1": ToolConfig({"key": "value"})}
    auto_execute_setting = True

    runtime = agent_factory_instance.create_agent_runtime(
        agent_id="test_rt_id_1",
        definition=sample_agent_definition, # sample_agent_definition implicitly has use_xml_tool_format=True
        llm_model_name=sample_llm_model_name,
        workspace=None, 
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )

    agent_factory_instance.create_agent_context.assert_called_once_with(
        agent_id="test_rt_id_1",
        definition=sample_agent_definition, # definition itself carries use_xml_tool_format
        llm_model_name=sample_llm_model_name,
        workspace=None,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )
    agent_factory_instance._get_default_event_handler_registry.assert_called_once()
    MockAgentRuntimeCls.assert_called_once_with(context=mock_created_context, event_handler_registry=mock_event_registry)
    assert runtime == MockAgentRuntimeCls.return_value

