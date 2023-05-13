import pytest
from llm_workflow_core.types.base_workflow import BaseWorkflow
from llm_workflow_core.types.workflow_template_config import StageTemplateConfig
from llm_workflow_core.types.workflow_instance import WorkflowInstance
from llm_workflow_core.types.base_stage import BaseStage

class Stage1(BaseStage):
    def construct_prompt(self):
        return "Prompt"

    def process_response(self, response):
        pass

    def execute(self):
        self.result = "Result"

class Stage2(BaseStage):
    def construct_prompt(self):
        # Implement the logic for constructing the prompt
        pass

    def process_response(self, response):
        # Implement the logic for processing the response
        pass

    # If the execute() method is required for Stage2, implement it as well:
    def execute(self):
        # Implement the logic for executing the stage
        pass


@pytest.fixture
def stages_config():
    return {
        'stage1': StageTemplateConfig(stage_class=Stage1),
        'stage2': StageTemplateConfig(stage_class=Stage2)
    }

@pytest.fixture
def workflow():
    return BaseWorkflow()

def test_workflow_instance_is_initialized_with_given_workflow_and_stages_config(workflow, stages_config):
    workflow_instance = WorkflowInstance(workflow, stages_config)
    assert isinstance(workflow_instance.stages['stage1'], Stage1)
    assert isinstance(workflow_instance.stages['stage2'], Stage2)

def test_workflow_instance_executes_valid_stage_and_returns_correct_result(workflow, stages_config):
    workflow_instance = WorkflowInstance(workflow, stages_config)
    result = workflow_instance.execute_stage('stage1')
    assert result == "Result"

def test_workflow_instance_raises_error_for_invalid_stage_execution(workflow, stages_config):
    workflow_instance = WorkflowInstance(workflow, stages_config)
    with pytest.raises(ValueError, match=r"Invalid stage_id: invalid_stage"):
        workflow_instance.execute_stage('invalid_stage')
