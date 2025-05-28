# file: autobyteus/tests/unit_tests/agent/registry/test_agent_registry.py
from typing import Any, Optional, Dict
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from autobyteus.agent.registry.agent_registry import AgentRegistry, default_agent_registry
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.agent import Agent
from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.utils.llm_config import LLMConfig 
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.agent.context import AgentContext 
from autobyteus.agent.status import AgentStatus 

# Fixtures for AgentDefinition
@pytest.fixture
def sample_agent_def():
    # use_xml_tool_format will default to True
    return AgentDefinition(
        name="TestRegAgent",
        role="registry_tester",
        description="Agent for testing registry",
        system_prompt="You are a test agent.",
        tool_names=[]
    )

@pytest.fixture 
def sample_agent_def2():
    # use_xml_tool_format will default to True
    return AgentDefinition(
        name="OtherAgent", 
        role="other_role", 
        description="desc", 
        system_prompt="sys", 
        tool_names=[]
    )

@pytest.fixture
def sample_llm_model_name_reg(): 
    return "GPT_4o_API" 

@pytest.fixture
def mock_agent_factory():
    factory = MagicMock(spec=AgentFactory)
    
    _known_mock_runtime_instance = MagicMock(spec=AgentRuntime)
    _known_mock_runtime_instance.context = MagicMock(spec=AgentContext)
    _known_mock_runtime_instance.context.agent_id = "default_mock_agent_id" 
    _known_mock_runtime_instance.context.definition = None 
    _known_mock_runtime_instance.context.status = MagicMock(spec=AgentStatus)
    _known_mock_runtime_instance.context.status.value = "mocked_status_value_via_context"


    def create_agent_runtime_mock_side_effect(agent_id: str,
                                             definition: AgentDefinition,
                                             llm_model_name: str, 
                                             workspace: Optional[BaseAgentWorkspace] = None,
                                             custom_llm_config: Optional[LLMConfig] = None, 
                                             custom_tool_config: Optional[Dict[str, ToolConfig]] = None, 
                                             auto_execute_tools: bool = True): 
        _known_mock_runtime_instance.context.agent_id = agent_id
        _known_mock_runtime_instance.context.definition = definition
        return _known_mock_runtime_instance

    factory.create_agent_runtime = MagicMock(side_effect=create_agent_runtime_mock_side_effect)
    factory._test_spy_runtime_instance = _known_mock_runtime_instance
    return factory

@pytest.fixture
def mock_definition_registry():
    return MagicMock(spec=AgentDefinitionRegistry)

@pytest.fixture
def agent_registry_instance(mock_agent_factory, mock_definition_registry):
    original_factory = default_agent_registry.agent_factory
    original_def_registry = default_agent_registry.definition_registry
    default_agent_registry.agent_factory = mock_agent_factory
    default_agent_registry.definition_registry = mock_definition_registry
    yield default_agent_registry 
    default_agent_registry.agent_factory = original_factory
    default_agent_registry.definition_registry = original_def_registry
    default_agent_registry._active_agents.clear()


# Test functions

def test_initialization(agent_registry_instance: AgentRegistry, mock_agent_factory, mock_definition_registry):
    assert agent_registry_instance.agent_factory == mock_agent_factory
    assert agent_registry_instance.definition_registry == mock_definition_registry
    assert isinstance(agent_registry_instance._active_agents, dict)

@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
def test_create_agent_successful(MockAgentClass: MagicMock, 
                                 agent_registry_instance: AgentRegistry,
                                 mock_agent_factory: MagicMock, 
                                 sample_agent_def: AgentDefinition,
                                 sample_llm_model_name_reg: str): 
    
    mock_agent_facade_instance = MockAgentClass.return_value
    
    with patch('random.randint', return_value=1234) as mock_randint:
        expected_agent_id = f"{sample_agent_def.name}_{sample_agent_def.role}_1234"
        mock_agent_facade_instance.agent_id = expected_agent_id

        assert agent_registry_instance.agent_factory is mock_agent_factory
        assert hasattr(agent_registry_instance.agent_factory, 'create_agent_runtime')
        assert isinstance(agent_registry_instance.agent_factory.create_agent_runtime, MagicMock)

        agent = agent_registry_instance.create_agent(
            definition=sample_agent_def,
            llm_model_name=sample_llm_model_name_reg 
        )

        mock_randint.assert_called_once()
        expected_runtime_instance = mock_agent_factory._test_spy_runtime_instance
            
        mock_agent_factory.create_agent_runtime.assert_called_once_with(
            agent_id=expected_agent_id,
            definition=sample_agent_def, # This definition carries use_xml_tool_format (default True)
            llm_model_name=sample_llm_model_name_reg, 
            workspace=None,
            custom_llm_config=None, 
            custom_tool_config=None, 
            auto_execute_tools=True 
        )
        MockAgentClass.assert_called_once_with(runtime=expected_runtime_instance)
        
        assert agent == mock_agent_facade_instance
        assert agent_registry_instance._active_agents[expected_agent_id] == mock_agent_facade_instance
        assert agent.agent_id == expected_agent_id


@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
def test_create_agent_id_collision(MockAgentClass: MagicMock,
                                   agent_registry_instance: AgentRegistry,
                                   mock_agent_factory: MagicMock, 
                                   sample_agent_def: AgentDefinition,
                                   sample_llm_model_name_reg: str): 
    
    def agent_constructor_side_effect(runtime):
        instance = MagicMock(spec=Agent)
        instance.agent_id = runtime.context.agent_id 
        return instance
    MockAgentClass.side_effect = agent_constructor_side_effect

    with patch('random.randint', return_value=5678):
        agent1 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model_name=sample_llm_model_name_reg)
        assert agent1.agent_id == f"{sample_agent_def.name}_{sample_agent_def.role}_5678"
    
    with patch('random.randint', side_effect=[5678, 5679]) as mock_rand_collision:
        agent2 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model_name=sample_llm_model_name_reg)
        
        assert mock_rand_collision.call_count == 2
        assert agent2.agent_id == f"{sample_agent_def.name}_{sample_agent_def.role}_5679"
        assert agent2.agent_id in agent_registry_instance._active_agents


def test_create_agent_invalid_input(agent_registry_instance: AgentRegistry, sample_llm_model_name_reg: str):
    with pytest.raises(ValueError, match="AgentDefinition cannot be None"):
        agent_registry_instance.create_agent(definition=None, llm_model_name=sample_llm_model_name_reg) # type: ignore
    with pytest.raises(TypeError, match="Expected AgentDefinition instance"):
        agent_registry_instance.create_agent(definition="not a definition", llm_model_name=sample_llm_model_name_reg) # type: ignore
    with pytest.raises(TypeError, match="An 'llm_model_name' \\(string\\) must be specified."):
        agent_registry_instance.create_agent(definition=MagicMock(spec=AgentDefinition), llm_model_name=None) # type: ignore
    with pytest.raises(TypeError, match="An 'llm_model_name' \\(string\\) must be specified."):
        agent_registry_instance.create_agent(definition=MagicMock(spec=AgentDefinition), llm_model_name=123) # type: ignore
    with pytest.raises(TypeError, match="custom_llm_config must be an LLMConfig instance or None."):
        agent_registry_instance.create_agent(
            definition=MagicMock(spec=AgentDefinition), 
            llm_model_name=sample_llm_model_name_reg,
            custom_llm_config="not an LLMConfig" # type: ignore
        )
    with pytest.raises(TypeError, match="custom_tool_config must be a Dict\\[str, ToolConfig\\] or None."):
        agent_registry_instance.create_agent(
            definition=MagicMock(spec=AgentDefinition), 
            llm_model_name=sample_llm_model_name_reg,
            custom_tool_config="not a dict" # type: ignore
        )
    with pytest.raises(TypeError, match="custom_tool_config must be a Dict\\[str, ToolConfig\\] or None."): 
        agent_registry_instance.create_agent(
            definition=MagicMock(spec=AgentDefinition),
            llm_model_name=sample_llm_model_name_reg,
            custom_tool_config={"tool_a": "not a ToolConfig"} # type: ignore
        )


@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
async def test_get_agent(MockAgentClass: MagicMock,
                         agent_registry_instance: AgentRegistry, 
                         sample_agent_def: AgentDefinition, 
                         sample_llm_model_name_reg: str): 
    
    MockAgentClass.side_effect = lambda runtime: MagicMock(spec=Agent, agent_id=runtime.context.agent_id)

    with patch('random.randint', return_value=7777): 
        created_agent = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model_name=sample_llm_model_name_reg)
        expected_id = f"{sample_agent_def.name}_{sample_agent_def.role}_7777"
        assert created_agent.agent_id == expected_id
        
    retrieved_agent = agent_registry_instance.get_agent(created_agent.agent_id)
    assert retrieved_agent is created_agent 
    assert agent_registry_instance.get_agent("non_existent_id") is None

@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
async def test_remove_agent(MockAgentClass: MagicMock,
                            agent_registry_instance: AgentRegistry, 
                            sample_agent_def: AgentDefinition, 
                            sample_llm_model_name_reg: str): 
    
    mock_agent_instance = MagicMock(spec=Agent)
    mock_agent_instance.stop = AsyncMock() 
    
    def agent_constructor_side_effect_for_remove(runtime):
        mock_agent_instance.agent_id = runtime.context.agent_id
        return mock_agent_instance
    MockAgentClass.side_effect = agent_constructor_side_effect_for_remove
    
    agent_to_remove = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model_name=sample_llm_model_name_reg)
    agent_id = agent_to_remove.agent_id 
    
    assert agent_to_remove is mock_agent_instance 
    
    result = await agent_registry_instance.remove_agent(agent_id)
    assert result is True
    mock_agent_instance.stop.assert_called_once_with(timeout=10.0) 
    assert agent_id not in agent_registry_instance._active_agents

    result_non_existent = await agent_registry_instance.remove_agent("fake_id")
    assert result_non_existent is False

@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
def test_list_active_agent_ids(MockAgentClass: MagicMock,
                               agent_registry_instance: AgentRegistry, 
                               sample_agent_def: AgentDefinition, 
                               sample_agent_def2: AgentDefinition, 
                               sample_llm_model_name_reg: str): 
    
    MockAgentClass.side_effect = lambda runtime: MagicMock(spec=Agent, agent_id=runtime.context.agent_id)

    assert agent_registry_instance.list_active_agent_ids() == []
    
    with patch('random.randint', return_value=1001):
        agent1 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model_name=sample_llm_model_name_reg)
    
    with patch('random.randint', return_value=1002):
        agent2 = agent_registry_instance.create_agent(definition=sample_agent_def2, llm_model_name=sample_llm_model_name_reg)

    ids = agent_registry_instance.list_active_agent_ids()
    assert len(ids) == 2
    assert agent1.agent_id in ids
    assert agent2.agent_id in ids

