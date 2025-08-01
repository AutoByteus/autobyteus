# file: autobyteus/tests/unit_tests/workflow/test_workflow_builder.py
import pytest
from unittest.mock import patch, MagicMock

from autobyteus.workflow.workflow_builder import WorkflowBuilder
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.context import WorkflowConfig, WorkflowNodeConfig
from autobyteus.agent.context import AgentConfig
from autobyteus.workflow.factory import WorkflowFactory
from autobyteus.utils.singleton import SingletonMeta

@pytest.fixture(autouse=True)
def clear_factory_singleton():
    """Ensures a clean WorkflowFactory state for each test."""
    if SingletonMeta in WorkflowFactory.__mro__:
        # Access the class-level instance dictionary and clear it
        if hasattr(WorkflowFactory, '_instances'):
            WorkflowFactory._instances.clear()

# The agent_config_factory fixture is automatically available from conftest.py

def test_build_successful_workflow(agent_config_factory):
    """
    Tests the happy path of building a workflow with a coordinator and a dependent node.
    """
    coordinator_config = agent_config_factory("Coordinator")
    member_config = agent_config_factory("Member")
    description = "Test workflow description"

    # Mock the WorkflowFactory to inspect what `build` passes to it.
    with patch('autobyteus.workflow.workflow_builder.WorkflowFactory') as MockWorkflowFactory:
        mock_factory_instance = MockWorkflowFactory.return_value
        mock_workflow_instance = MagicMock(spec=AgenticWorkflow)
        mock_factory_instance.create_workflow.return_value = mock_workflow_instance

        builder = WorkflowBuilder(description=description)
        
        # Chain the calls to build the graph
        workflow = (
            builder
            .set_coordinator(coordinator_config)
            .add_node(member_config, dependencies=[coordinator_config])
            .build()
        )

        # Assert that the factory's create_workflow method was called
        mock_factory_instance.create_workflow.assert_called_once()
        
        # Get the WorkflowConfig object that was passed to the factory
        final_workflow_config: WorkflowConfig = mock_factory_instance.create_workflow.call_args.kwargs['config']
        
        # Assert the created workflow is the one returned by the mock factory
        assert workflow is mock_workflow_instance
        
        # Assert properties of the generated WorkflowConfig
        assert final_workflow_config.description == description
        assert len(final_workflow_config.nodes) == 2
        
        # Find the coordinator and member nodes in the final config
        final_coord_node = final_workflow_config.coordinator_node
        final_member_node = next(n for n in final_workflow_config.nodes if n.agent_config == member_config)

        assert final_coord_node.agent_config == coordinator_config
        assert final_member_node.agent_config == member_config
        
        # Assert the dependency was set correctly
        assert len(final_member_node.dependencies) == 1
        assert final_member_node.dependencies[0] is final_coord_node

def test_build_fails_without_coordinator(agent_config_factory):
    """
    Tests that build() raises a ValueError if a coordinator has not been set.
    """
    builder = WorkflowBuilder(description="A workflow without a coordinator")
    builder.add_node(agent_config_factory("SomeNode"))
    
    with pytest.raises(ValueError, match="A coordinator must be set"):
        builder.build()

def test_set_coordinator_fails_if_called_twice(agent_config_factory):
    """
    Tests that set_coordinator() raises a ValueError if called more than once.
    """
    coord1_config = agent_config_factory("Coord1")
    coord2_config = agent_config_factory("Coord2")
    
    builder = WorkflowBuilder(description="Test double coordinator")
    builder.set_coordinator(coord1_config)
    
    with pytest.raises(ValueError, match="A coordinator has already been set"):
        builder.set_coordinator(coord2_config)

def test_add_node_fails_with_duplicate_config(agent_config_factory):
    """
    Tests that add_node() raises a ValueError for a duplicate AgentConfig.
    """
    node_config = agent_config_factory("MyNode")
    
    builder = WorkflowBuilder(description="Test duplicate node")
    builder.add_node(node_config)
    
    with pytest.raises(ValueError, match="has already been added"):
        builder.add_node(node_config)

def test_add_node_fails_with_unknown_dependency(agent_config_factory):
    """
    Tests that add_node() raises a ValueError if a dependency hasn't been added.
    """
    node_config = agent_config_factory("MyNode")
    dependency_config = agent_config_factory("UnseenDependency")
    
    builder = WorkflowBuilder(description="Test unknown dependency")
    
    with pytest.raises(ValueError, match="must be added to the builder before being used"):
        builder.add_node(node_config, dependencies=[dependency_config])
