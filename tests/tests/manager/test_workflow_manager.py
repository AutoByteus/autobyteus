import pytest
from llm_workflow_core.registry.workflow_registry import WorkflowRegistry
from llm_workflow_core.manager.workflow_manager import WorkflowManager
from llm_workflow_core.types.base_workflow import BaseWorkflow
from llm_workflow_core.types.workflow_template_config import StageTemplateConfig
from tests.types.test_workflow_instance import Stage1, Stage2

class TestWorkflow(BaseWorkflow):
    config = {
        'stages': {
            'stage1': StageTemplateConfig(stage_class=Stage1),
            'stage2': StageTemplateConfig(stage_class=Stage2)
        }
    }

@pytest.fixture
def workflow_registry():
    registry = WorkflowRegistry()
    registry.register_workflow("test_workflow", TestWorkflow, {})
    return registry


@pytest.fixture
def workflow_manager(workflow_registry):
    return WorkflowManager(workflow_registry)


def test_workflow_manager_is_initialized_with_given_workflow_registry(workflow_registry):
    workflow_manager = WorkflowManager(workflow_registry)
    assert isinstance(workflow_manager, WorkflowManager)


def test_new_workflow_instance_is_initialized_correctly(workflow_manager: WorkflowManager):
    workflow_id = workflow_manager.initialize_workflow("test_workflow")
    assert workflow_id is not None


def test_workflow_stage_is_executed_correctly(workflow_manager: WorkflowManager):
    workflow_id = workflow_manager.initialize_workflow("test_workflow")
    result = workflow_manager.execute_stage(workflow_id, "stage1")
    assert result == "Result"


def test_workflow_stage_execution_returns_error_for_invalid_workflow_id(workflow_manager:WorkflowManager):
    result = workflow_manager.execute_stage("invalid_workflow_id", "stage1")
    assert result == "Invalid workflow_id: invalid_workflow_id"
