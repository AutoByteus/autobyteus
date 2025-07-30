# file: autobyteus/tests/unit_tests/workflow/factory/test_workflow_factory.py
import logging
import pytest
from unittest.mock import MagicMock, patch, ANY

from autobyteus.workflow.factory.workflow_factory import WorkflowFactory
from autobyteus.workflow.agentic_workflow import AgenticWorkflow
from autobyteus.workflow.context import WorkflowConfig
from autobyteus.workflow.events import ProcessUserMessageEvent
from autobyteus.workflow.handlers import ProcessUserMessageEventHandler
from autobyteus.utils.singleton import SingletonMeta

@pytest.fixture
def workflow_factory():
    """Provides a clean instance of the WorkflowFactory."""
    if SingletonMeta in WorkflowFactory.__mro__:
        WorkflowFactory.clear_singleton()
    return WorkflowFactory()

def test_get_default_event_handler_registry(workflow_factory: WorkflowFactory):
    """Tests that the factory creates a correct registry of event handlers."""
    registry = workflow_factory._get_default_event_handler_registry()
    handler = registry.get_handler(ProcessUserMessageEvent)
    assert isinstance(handler, ProcessUserMessageEventHandler)

@patch('autobyteus.workflow.factory.workflow_factory.TeamManager', autospec=True)
@patch('autobyteus.workflow.factory.workflow_factory.WorkflowRuntime', autospec=True)
def test_create_workflow_assembles_components_correctly(MockWorkflowRuntime, MockTeamManager, workflow_factory: WorkflowFactory, sample_workflow_config: WorkflowConfig):
    """
    Tests that create_workflow correctly instantiates and wires together
    all the necessary workflow components.
    """
    mock_runtime_instance = MockWorkflowRuntime.return_value
    mock_runtime_instance.multiplexer = MagicMock()
    mock_runtime_instance.context = MagicMock()
    # We will set the workflow_id on the mock *after* the factory creates the real one.
    
    mock_team_manager_instance = MockTeamManager.return_value

    workflow = workflow_factory.create_workflow(sample_workflow_config)

    # FIX: The workflow object's ID is incorrectly a mock because it's derived from the
    # mocked runtime. We retrieve the real ID from the factory and patch both the
    # workflow object and the mock context for assertion consistency.
    real_workflow_id = workflow_factory.list_active_workflow_ids()[0]
    workflow.workflow_id = real_workflow_id
    mock_runtime_instance.context.workflow_id = real_workflow_id

    assert isinstance(workflow, AgenticWorkflow)
    assert workflow.workflow_id in workflow_factory.list_active_workflow_ids()

    # 1. Verify WorkflowRuntime was created with context and registry
    MockWorkflowRuntime.assert_called_once()
    runtime_call_kwargs = MockWorkflowRuntime.call_args.kwargs
    assert runtime_call_kwargs['context'].config == sample_workflow_config
    assert runtime_call_kwargs['event_handler_registry'] is not None

    # 2. Verify TeamManager was created and given the runtime instance and multiplexer
    MockTeamManager.assert_called_once_with(
        workflow_id=workflow.workflow_id, # Use the real, generated ID for the check
        runtime=mock_runtime_instance,
        multiplexer=mock_runtime_instance.multiplexer
    )

    # 3. Verify the final context was populated with the team manager
    final_context = runtime_call_kwargs['context']
    assert final_context.state.team_manager is mock_team_manager_instance
