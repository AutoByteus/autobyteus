# file: autobyteus/tests/unit_tests/agent/registry/test_agent_registry.py
from typing import Any, Optional
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY

from autobyteus.agent.registry.agent_registry import AgentRegistry, default_agent_registry, default_definition_registry_instance, default_agent_factory
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.registry.agent_definition_registry import AgentDefinitionRegistry
from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.agent import Agent
from autobyteus.agent.agent_runtime import AgentRuntime
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.llm.models import LLMModel
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.agent.context import AgentContext
from autobyteus.agent.status import AgentStatus

# Fixtures for AgentDefinition and LLMModel
@pytest.fixture
def sample_agent_def():
    return AgentDefinition(
        name="TestRegAgent",
        role="registry_tester",
        description="Agent for testing registry",
        system_prompt="You are a test agent.",
        tool_names=[]
    )

@pytest.fixture
def sample_llm_model_reg(): # Renamed to avoid conflict
    return LLMModel.GPT_4o_API # Any valid model

@pytest.fixture
def mock_agent_factory():
    factory = MagicMock(spec=AgentFactory)
    
    # This known_mock_runtime will be configured by the side_effect and returned.
    # The test must use this *same object* for assertion.
    _known_mock_runtime_instance = MagicMock(spec=AgentRuntime)
    _known_mock_runtime_instance.context = MagicMock(spec=AgentContext)
    _known_mock_runtime_instance.context.status = MagicMock(spec=AgentStatus)
    _known_mock_runtime_instance.context.status.value = "mocked_status_value_via_context"

    def create_agent_runtime_mock_side_effect(agent_id: str,
                                             definition: AgentDefinition,
                                             llm_model: LLMModel,
                                             workspace: Optional[BaseAgentWorkspace] = None,
                                             llm_config_override: Optional[dict[str, Any]] = None,
                                             tool_config_override: Optional[dict[str, ToolConfig]] = None,
                                             auto_execute_tools_override: bool = True):
        _known_mock_runtime_instance.context.agent_id = agent_id
        _known_mock_runtime_instance.context.definition = definition
        # If other args are needed by Agent constructor via runtime, set them here if necessary.
        # For example, if Agent.__init__ reads runtime.context.llm_model:
        # _known_mock_runtime_instance.context.llm_model = llm_model 
        return _known_mock_runtime_instance

    factory.create_agent_runtime = MagicMock(side_effect=create_agent_runtime_mock_side_effect)
    
    # Attach the known instance to the factory mock so tests can access it.
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


# Test functions (refactored from TestAgentRegistry class)

def test_initialization(agent_registry_instance: AgentRegistry, mock_agent_factory, mock_definition_registry):
    assert agent_registry_instance.agent_factory == mock_agent_factory
    assert agent_registry_instance.definition_registry == mock_definition_registry
    assert isinstance(agent_registry_instance._active_agents, dict)

@patch('autobyteus.agent.registry.agent_registry.Agent', autospec=True)
def test_create_agent_successful(MockAgent, agent_registry_instance: AgentRegistry,
                                 mock_agent_factory: AgentFactory, sample_agent_def: AgentDefinition,
                                 sample_llm_model_reg: LLMModel):
    
    # mock_created_runtime and its context setup are now handled by the mock_agent_factory fixture's side_effect
    # and the _test_spy_runtime_instance.
    
    with patch('random.randint', return_value=1234) as mock_randint:
        expected_agent_id = f"{sample_agent_def.name}_{sample_agent_def.role}_1234"
        
        # This mock_agent_instance_facade is the mock for the Agent object returned by Agent(...)
        mock_agent_instance_facade = MockAgent.return_value 
        # The agent_id of the facade should match the expected_agent_id.
        # This is set because Agent.__init__ does self.agent_id = runtime.context.agent_id
        # and the side_effect in mock_agent_factory ensures runtime.context.agent_id is correct.
        mock_agent_instance_facade.agent_id = expected_agent_id


        agent = agent_registry_instance.create_agent(
            definition=sample_agent_def,
            llm_model=sample_llm_model_reg
        )

        mock_randint.assert_called_once()
        
        # This is the runtime instance that the factory's side_effect configured and returned,
        # and thus was passed to Agent() constructor.
        expected_runtime_instance_for_assertion = mock_agent_factory._test_spy_runtime_instance
            
        mock_agent_factory.create_agent_runtime.assert_called_once_with(
            agent_id=expected_agent_id,
            definition=sample_agent_def,
            llm_model=sample_llm_model_reg,
            workspace=None,
            llm_config_override=None,
            tool_config_override=None,
            auto_execute_tools_override=True
        )
        # Assert that MockAgent (the patched Agent class) was called with the correct runtime instance
        MockAgent.assert_called_once_with(runtime=expected_runtime_instance_for_assertion)
        
        assert agent == mock_agent_instance_facade # The agent returned by create_agent should be the mock facade
        assert agent_registry_instance._active_agents[expected_agent_id] == mock_agent_instance_facade
        assert agent.agent_id == expected_agent_id

def test_create_agent_id_collision(agent_registry_instance: AgentRegistry,
                                    mock_agent_factory: AgentFactory, sample_agent_def: AgentDefinition,
                                    sample_llm_model_reg: LLMModel):
    # First agent creation
    with patch('random.randint', return_value=5678):
        agent1 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model=sample_llm_model_reg)
        assert agent1.agent_id == f"{sample_agent_def.name}_{sample_agent_def.role}_5678"
    
    # Second agent creation, simulate ID collision then success
    with patch('random.randint', side_effect=[5678, 5679]) as mock_rand_collision:
        agent2 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model=sample_llm_model_reg)
        
        assert mock_rand_collision.call_count == 2
        assert agent2.agent_id == f"{sample_agent_def.name}_{sample_agent_def.role}_5679"
        assert agent2.agent_id in agent_registry_instance._active_agents


def test_create_agent_invalid_input(agent_registry_instance: AgentRegistry, sample_llm_model_reg: LLMModel):
    with pytest.raises(ValueError, match="AgentDefinition cannot be None"):
        agent_registry_instance.create_agent(definition=None, llm_model=sample_llm_model_reg) # type: ignore
    
    with pytest.raises(TypeError, match="Expected AgentDefinition instance"):
        agent_registry_instance.create_agent(definition="not a definition", llm_model=sample_llm_model_reg) # type: ignore

    with pytest.raises(TypeError, match="An 'llm_model' of type LLMModel must be specified"):
        agent_registry_instance.create_agent(definition=MagicMock(spec=AgentDefinition), llm_model="not llm model") # type: ignore


async def test_get_agent(agent_registry_instance: AgentRegistry, sample_agent_def: AgentDefinition, sample_llm_model_reg: LLMModel):
    with patch('random.randint', return_value=7777): 
        created_agent = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model=sample_llm_model_reg)
        expected_id = f"{sample_agent_def.name}_{sample_agent_def.role}_7777"
        assert created_agent.agent_id == expected_id
        
    retrieved_agent = agent_registry_instance.get_agent(created_agent.agent_id)
    assert retrieved_agent == created_agent 

    assert agent_registry_instance.get_agent("non_existent_id") is None

async def test_remove_agent(agent_registry_instance: AgentRegistry, sample_agent_def: AgentDefinition, sample_llm_model_reg: LLMModel):
    agent_to_remove = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model=sample_llm_model_reg)
    agent_id = agent_to_remove.agent_id
    
    agent_to_remove.stop = AsyncMock() 

    result = await agent_registry_instance.remove_agent(agent_id)
    assert result is True
    agent_to_remove.stop.assert_called_once_with(timeout=10.0)
    assert agent_id not in agent_registry_instance._active_agents

    result_non_existent = await agent_registry_instance.remove_agent("fake_id")
    assert result_non_existent is False

def test_list_active_agent_ids(agent_registry_instance: AgentRegistry, sample_agent_def: AgentDefinition, sample_llm_model_reg: LLMModel):
    assert agent_registry_instance.list_active_agent_ids() == []
    agent1 = agent_registry_instance.create_agent(definition=sample_agent_def, llm_model=sample_llm_model_reg)
    
    sample_agent_def2 = AgentDefinition(name="OtherAgent", role="other_role", description="desc", system_prompt="sys", tool_names=[])
    agent2 = agent_registry_instance.create_agent(definition=sample_agent_def2, llm_model=sample_llm_model_reg)

    ids = agent_registry_instance.list_active_agent_ids()
    assert len(ids) == 2
    assert agent1.agent_id in ids
    assert agent2.agent_id in ids
