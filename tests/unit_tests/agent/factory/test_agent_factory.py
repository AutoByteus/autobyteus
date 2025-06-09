import pytest
from unittest.mock import MagicMock, patch, ANY

from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.registry.agent_specification import AgentSpecification
from autobyteus.agent.context import AgentConfig, AgentRuntimeState, AgentContext
from autobyteus.agent.events import (
    UserMessageReceivedEvent, AgentErrorEvent, AgentStoppedEvent, AgentReadyEvent,
    BootstrapAgentEvent,
    InterAgentMessageReceivedEvent, LLMCompleteResponseReceivedEvent, PendingToolInvocationEvent,
    ToolResultEvent, GenericEvent, ToolExecutionApprovalEvent, LLMUserMessageReadyEvent, ApprovedToolInvocationEvent,
)
from autobyteus.agent.handlers import (
    EventHandlerRegistry, UserInputMessageEventHandler, LifecycleEventLogger,
    BootstrapAgentEventHandler,
    InterAgentMessageReceivedEventHandler, LLMCompleteResponseReceivedEventHandler, ToolInvocationRequestEventHandler,
    ToolResultEventHandler, GenericEventHandler, ToolExecutionApprovalEventHandler, LLMUserMessageReadyEventHandler,
    ApprovedToolInvocationEventHandler
)
from autobyteus.agent.runtime.agent_runtime import AgentRuntime
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.utils.llm_config import LLMConfig 
from autobyteus.tools.registry import ToolRegistry
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.agent.system_prompt_processor import SystemPromptProcessorRegistry, default_system_prompt_processor_registry

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
def sample_agent_specification():
    return AgentSpecification(
        name="SampleAgent",
        role="tester",
        description="A sample agent for testing.",
        system_prompt="You are a helpful testing assistant. {{tools}} {{tool_examples}}",
        tool_names=["tool1", "tool2"],
        input_processor_names=["PassthroughInputProcessor"],
        use_xml_tool_format=True 
    )

@pytest.fixture
def sample_agent_specification_json_format():
    return AgentSpecification(
        name="SampleAgentJson",
        role="testerJson",
        description="A sample agent for testing JSON format.",
        system_prompt="You are a helpful testing assistant (JSON). {{tools}} {{tool_examples}}",
        tool_names=["tool_json1", "tool_json2"],
        use_xml_tool_format=False 
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

    bootstrap_handler = registry.get_handler(BootstrapAgentEvent)
    assert isinstance(bootstrap_handler, BootstrapAgentEventHandler)
    assert bootstrap_handler.tool_registry == agent_factory_instance.tool_registry
    assert bootstrap_handler.system_prompt_processor_registry == agent_factory_instance.system_prompt_processor_registry
    assert bootstrap_handler.llm_factory == agent_factory_instance.llm_factory
    
    assert isinstance(registry.get_handler(UserMessageReceivedEvent), UserInputMessageEventHandler)
    assert isinstance(registry.get_handler(InterAgentMessageReceivedEvent), InterAgentMessageReceivedEventHandler)
    assert isinstance(registry.get_handler(LLMCompleteResponseReceivedEvent), LLMCompleteResponseReceivedEventHandler)
    assert isinstance(registry.get_handler(PendingToolInvocationEvent), ToolInvocationRequestEventHandler)
    assert isinstance(registry.get_handler(ToolResultEvent), ToolResultEventHandler)
    assert isinstance(registry.get_handler(GenericEvent), GenericEventHandler)
    assert isinstance(registry.get_handler(ToolExecutionApprovalEvent), ToolExecutionApprovalEventHandler)
    assert isinstance(registry.get_handler(LLMUserMessageReadyEvent), LLMUserMessageReadyEventHandler)
    assert isinstance(registry.get_handler(ApprovedToolInvocationEvent), ApprovedToolInvocationEventHandler)
    
    lifecycle_logger_instance = registry.get_handler(AgentReadyEvent) 
    assert isinstance(lifecycle_logger_instance, LifecycleEventLogger)
    assert registry.get_handler(AgentStoppedEvent) is lifecycle_logger_instance
    assert registry.get_handler(AgentErrorEvent) is lifecycle_logger_instance


@patch('autobyteus.agent.factory.agent_factory.AgentConfig', autospec=True)
@patch('autobyteus.agent.factory.agent_factory.AgentRuntimeState', autospec=True)
def test_create_agent_config_and_state_successful(
    MockAgentRuntimeState, MockAgentConfig,
    agent_factory_instance: AgentFactory,
    sample_agent_specification: AgentSpecification,
    sample_llm_model_name: str):

    mock_workspace = MagicMock(spec=BaseAgentWorkspace)
    custom_llm_config_obj = LLMConfig(temperature=0.8)
    tool_config_data_dict = {"tool_specific_key": "tool_specific_value"}
    custom_tool_config_obj = {"tool1": ToolConfig(params=tool_config_data_dict)} 
    auto_execute_setting = False

    created_config, created_state = agent_factory_instance._create_agent_config_and_state(
        agent_id="test_agent_id_001",
        specification=sample_agent_specification,
        llm_model_name=sample_llm_model_name,
        workspace=mock_workspace,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )

    MockAgentConfig.assert_called_once_with(
        agent_id="test_agent_id_001",
        specification=sample_agent_specification,
        auto_execute_tools=auto_execute_setting, 
        llm_model_name=sample_llm_model_name,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj
    )
    assert created_config == MockAgentConfig.return_value
    
    MockAgentRuntimeState.assert_called_once_with(
        agent_id="test_agent_id_001", 
        workspace=mock_workspace,
    )
    assert created_state == MockAgentRuntimeState.return_value


@patch('autobyteus.agent.factory.agent_factory.AgentContext', autospec=True)
def test_create_agent_context_successful(
    MockAgentContextCls,
    agent_factory_instance: AgentFactory,
    sample_agent_specification: AgentSpecification,
    sample_llm_model_name: str):

    mock_workspace = MagicMock(spec=BaseAgentWorkspace)
    custom_llm_config_obj = LLMConfig(temperature=0.8)
    custom_tool_config_obj = {"tool1": ToolConfig(params={"key": "value"})} 
    auto_execute_setting = False

    mock_created_config_instance = MagicMock(spec=AgentConfig)
    mock_created_state_instance = MagicMock(spec=AgentRuntimeState)
    
    with patch.object(agent_factory_instance, '_create_agent_config_and_state', return_value=(mock_created_config_instance, mock_created_state_instance)) as mock_create_config_state_method:
        
        context = agent_factory_instance.create_agent_context(
            agent_id="test_ctx_id_1",
            specification=sample_agent_specification,
            llm_model_name=sample_llm_model_name,
            workspace=mock_workspace,
            custom_llm_config=custom_llm_config_obj,
            custom_tool_config=custom_tool_config_obj,
            auto_execute_tools=auto_execute_setting
        )

        mock_create_config_state_method.assert_called_once_with(
            agent_id="test_ctx_id_1",
            specification=sample_agent_specification,
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
    sample_spec = MagicMock(spec=AgentSpecification)
    sample_spec.name = "TestSpec" 
    sample_spec.use_xml_tool_format = True 
    
    with pytest.raises(TypeError, match="Expected AgentSpecification"):
        agent_factory_instance.create_agent_context(agent_id="id", specification="not a specification", llm_model_name=sample_llm_model_name) # type: ignore
    
    agent_config_module = 'autobyteus.agent.context.agent_config.AgentConfig'
    with patch(agent_config_module, autospec=True) as mock_agent_config_cls:
        with pytest.raises(ValueError):
            # This validation is inside AgentConfig.__init__ which we can't easily bypass
            # without more complex mocking. Let's assume the call to create_agent_config_and_state
            # would fail. A direct call check is simpler.
            agent_factory_instance._create_agent_config_and_state("id", sample_spec, llm_model_name=None)
        
        with pytest.raises(TypeError):
            agent_factory_instance._create_agent_config_and_state(
                "id", sample_spec, sample_llm_model_name, workspace="not a workspace")
        
        with pytest.raises(TypeError):
            agent_factory_instance._create_agent_config_and_state(
                "id", sample_spec, sample_llm_model_name, custom_llm_config={"temp": 0.5}) # type: ignore
        
        with pytest.raises(TypeError):
            agent_factory_instance._create_agent_config_and_state(
                "id", sample_spec, sample_llm_model_name, custom_tool_config={"tool1": {"cfg": "val"}}) # type: ignore
        
        with pytest.raises(TypeError):
            agent_factory_instance._create_agent_config_and_state(
                "id", sample_spec, sample_llm_model_name, 
                custom_tool_config={"tool1": "not_a_tool_config_object"} # type: ignore
            )


@patch('autobyteus.agent.factory.agent_factory.AgentRuntime', autospec=True)
def test_create_agent_runtime(MockAgentRuntimeCls, agent_factory_instance: AgentFactory,
                              sample_agent_specification: AgentSpecification,
                              sample_llm_model_name: str):
    
    mock_created_context_instance = MagicMock(spec=AgentContext)
    agent_factory_instance.create_agent_context = MagicMock(return_value=mock_created_context_instance)
    
    mock_event_registry_instance = MagicMock(spec=EventHandlerRegistry)
    agent_factory_instance._get_default_event_handler_registry = MagicMock(return_value=mock_event_registry_instance)

    custom_llm_config_obj = LLMConfig(temperature=0.1)
    custom_tool_config_obj = {"tool1": ToolConfig(params={"key": "value"})} 
    auto_execute_setting = True
    test_agent_id = "test_rt_id_1"
    mock_workspace_arg = MagicMock(spec=BaseAgentWorkspace)


    runtime = agent_factory_instance.create_agent_runtime(
        agent_id=test_agent_id,
        specification=sample_agent_specification,
        llm_model_name=sample_llm_model_name,
        workspace=mock_workspace_arg, 
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )

    agent_factory_instance.create_agent_context.assert_called_once_with(
        agent_id=test_agent_id,
        specification=sample_agent_specification,
        llm_model_name=sample_llm_model_name,
        workspace=mock_workspace_arg,
        custom_llm_config=custom_llm_config_obj,
        custom_tool_config=custom_tool_config_obj,
        auto_execute_tools=auto_execute_setting
    )
    agent_factory_instance._get_default_event_handler_registry.assert_called_once()
    MockAgentRuntimeCls.assert_called_once_with(context=mock_created_context_instance, event_handler_registry=mock_event_registry_instance)
    assert runtime == MockAgentRuntimeCls.return_value
