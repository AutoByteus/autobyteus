# file: autobyteus/tests/unit_tests/agent_team/test_agent_team_builder.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
from autobyteus.agent_team.agent_team import AgentTeam
from autobyteus.agent_team.context import AgentTeamConfig, TeamNodeConfig
from autobyteus.agent.context import AgentConfig
from autobyteus.agent_team.factory import AgentTeamFactory
from autobyteus.utils.singleton import SingletonMeta

@pytest.fixture(autouse=True)
def clear_factory_singleton():
    """Ensures a clean AgentTeamFactory state for each test."""
    if SingletonMeta in AgentTeamFactory.__mro__:
        if hasattr(AgentTeamFactory, '_instances'):
            AgentTeamFactory._instances.clear()

def test_build_successful_team(agent_config_factory):
    """
    Tests the happy path of building a team with a coordinator and a dependent node.
    """
    coordinator_config = agent_config_factory("Coordinator")
    member_config = agent_config_factory("Member")
    description = "Test team description"
    name = "TestTeam"

    with patch('autobyteus.agent_team.agent_team_builder.AgentTeamFactory') as MockAgentTeamFactory:
        mock_factory_instance = MockAgentTeamFactory.return_value
        mock_team_instance = MagicMock(spec=AgentTeam)
        mock_factory_instance.create_team.return_value = mock_team_instance

        builder = AgentTeamBuilder(name=name, description=description)
        
        team = (
            builder
            .set_coordinator(coordinator_config)
            .add_agent_node(member_config, dependencies=[coordinator_config])
            .build()
        )

        mock_factory_instance.create_team.assert_called_once()
        
        final_team_config: AgentTeamConfig = mock_factory_instance.create_team.call_args.kwargs['config']
        
        assert team is mock_team_instance
        
        assert final_team_config.name == name
        assert final_team_config.description == description
        assert len(final_team_config.nodes) == 2
        
        final_coord_node = final_team_config.coordinator_node
        final_member_node = next(n for n in final_team_config.nodes if n.node_definition == member_config)

        assert final_coord_node.node_definition == coordinator_config
        assert final_member_node.node_definition == member_config
        
        assert len(final_member_node.dependencies) == 1
        assert final_member_node.dependencies[0] is final_coord_node

def test_build_fails_without_coordinator(agent_config_factory):
    """
    Tests that build() raises a ValueError if a coordinator has not been set.
    """
    builder = AgentTeamBuilder(name="Test", description="A team without a coordinator")
    builder.add_agent_node(agent_config_factory("SomeNode"))
    
    with pytest.raises(ValueError, match="A coordinator must be set"):
        builder.build()

def test_add_node_fails_with_duplicate_name(agent_config_factory):
    """
    Tests that adding a node with a name that's already in use raises a ValueError.
    """
    node1_config = agent_config_factory("DuplicateName")
    node2_config = agent_config_factory("DuplicateName")
    
    builder = AgentTeamBuilder(name="Test", description="Test duplicate name")
    builder.add_agent_node(node1_config)
    
    with pytest.raises(ValueError, match="Duplicate node name 'DuplicateName' detected"):
        builder.add_agent_node(node2_config)

def test_add_node_fails_with_unknown_dependency(agent_config_factory):
    """
    Tests that add_node() raises a ValueError if a dependency hasn't been added.
    """
    node_config = agent_config_factory("MyNode")
    dependency_config = agent_config_factory("UnseenDependency")
    
    builder = AgentTeamBuilder(name="Test", description="Test unknown dependency")
    
    with pytest.raises(ValueError, match="must be added to the builder before being used"):
        builder.add_agent_node(node_config, dependencies=[dependency_config])
