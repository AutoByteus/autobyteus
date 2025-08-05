# file: autobyteus/tests/unit_tests/agent_team/factory/test_agent_team_factory.py
import logging
import pytest
from unittest.mock import MagicMock, patch, ANY

from autobyteus.agent_team.factory.agent_team_factory import AgentTeamFactory
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.context import AgentTeamConfig
from autobyteus.agent_team.events import ProcessUserMessageEvent
from autobyteus.agent_team.handlers import ProcessUserMessageEventHandler
from autobyteus.utils.singleton import SingletonMeta

@pytest.fixture
def agent_team_factory():
    """Provides a clean instance of the AgentTeamFactory."""
    if SingletonMeta in AgentTeamFactory.__mro__:
        AgentTeamFactory.clear_singleton()
    return AgentTeamFactory()

def test_get_default_event_handler_registry(agent_team_factory: AgentTeamFactory):
    """Tests that the factory creates a correct registry of event handlers."""
    registry = agent_team_factory._get_default_event_handler_registry()
    handler = registry.get_handler(ProcessUserMessageEvent)
    assert isinstance(handler, ProcessUserMessageEventHandler)

@patch('autobyteus.agent_team.factory.agent_team_factory.TeamManager', autospec=True)
@patch('autobyteus.agent_team.factory.agent_team_factory.AgentTeamRuntime', autospec=True)
def test_create_team_assembles_components_correctly(MockAgentTeamRuntime, MockTeamManager, agent_team_factory: AgentTeamFactory, sample_agent_team_config: AgentTeamConfig):
    """
    Tests that create_team correctly instantiates and wires together
    all the necessary agent team components.
    """
    mock_runtime_instance = MockAgentTeamRuntime.return_value
    mock_runtime_instance.multiplexer = MagicMock()
    mock_runtime_instance.context = MagicMock()
    
    mock_team_manager_instance = MockTeamManager.return_value

    team = agent_team_factory.create_team(sample_agent_team_config)

    real_team_id = agent_team_factory.list_active_team_ids()[0]
    team.team_id = real_team_id
    mock_runtime_instance.context.team_id = real_team_id

    assert isinstance(team, AgentTeam)
    assert team.team_id in agent_team_factory.list_active_team_ids()

    # 1. Verify AgentTeamRuntime was created with context and registry
    MockAgentTeamRuntime.assert_called_once()
    runtime_call_kwargs = MockAgentTeamRuntime.call_args.kwargs
    assert runtime_call_kwargs['context'].config == sample_agent_team_config
    assert runtime_call_kwargs['event_handler_registry'] is not None

    # 2. Verify TeamManager was created and given the runtime instance and multiplexer
    MockTeamManager.assert_called_once_with(
        team_id=team.team_id,
        runtime=mock_runtime_instance,
        multiplexer=mock_runtime_instance.multiplexer
    )

    # 3. Verify the final context was populated with the team manager
    final_context = runtime_call_kwargs['context']
    assert final_context.state.team_manager is mock_team_manager_instance
