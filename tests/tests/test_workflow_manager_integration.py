import pytest
from llm_workflow_core.registry.workflow_registry import WorkflowRegistry
from llm_workflow_core.manager.workflow_manager import WorkflowManager
from automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow

@pytest.fixture
def workflow_registry():
    registry = WorkflowRegistry()
    # When: Registering the AutomatedCodingWorkflow
    workflow_package = "automated_coding_workflow"

    # When: Loading the workflow using the WorkflowRegistry
    config = {"workflows": {"enabled_workflows": [workflow_package]}}
    registry.load_enabled_workflows(config)
    return registry


@pytest.fixture
def workflow_manager(workflow_registry):
    return WorkflowManager(workflow_registry)

def test_given_valid_workflow_name_when_initializing_workflow_then_workflow_instance_is_created_and_stages_are_executed_correctly(workflow_manager: WorkflowManager):
    # Initialize the workflow
    workflow_id = workflow_manager.initialize_workflow("automated_coding_workflow")
    assert workflow_id is not None

    # Execute the stages in the correct order
    requirement_result = workflow_manager.execute_stage(workflow_id, "requirement")

    requirement_refine_result = workflow_manager.execute_stage(workflow_id, "refine")

    design_result = workflow_manager.execute_stage(workflow_id, "design")

    test_generation_result = workflow_manager.execute_stage(workflow_id, "test_generation")

    implementation_result = workflow_manager.execute_stage(workflow_id, "implementation")

    testing_result = workflow_manager.execute_stage(workflow_id, "testing")

