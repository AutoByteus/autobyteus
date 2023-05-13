"""
config.py
The WORKFLOW_CONFIG dictionary defines the structure of the workflow, including stages and substages.
Each stage is defined as a key-value pair, where the key is the stage name and the value is a dictionary containing:
    - 'stage_class': The class representing the stage.
    - 'stages': A dictionary of substages, if any, following the same structure.

For example, the 'requirement' stage has a 'refine' substage with its own class.
"""
from src.automated_coding_workflow.stages.requirement_refine_stage import RequirementRefineStage

from src.automated_coding_workflow.stages.requirement_stage import RequirementStage
from src.automated_coding_workflow.stages.design_stage import DesignStage
from src.automated_coding_workflow.stages.test_generation_stage import TestGenerationStage
from src.automated_coding_workflow.stages.implementation_stage import ImplementationStage
from src.automated_coding_workflow.stages.testing_stage import TestingStage
from src.workflow_types.types.workflow_template_config import WorkflowTemplateStagesConfig

WORKFLOW_CONFIG: WorkflowTemplateStagesConfig = {
    'stages': {
        'requirement': {
            'stage_class': RequirementStage,
            'stages': {
                'refine': {
                    'stage_class': RequirementRefineStage
                }
            },
        },
        'design': {
            'stage_class': DesignStage,
        },
        'test_generation': {
            'stage_class': TestGenerationStage,
        },
        'implementation': {
            'stage_class': ImplementationStage,
        },
        'testing': {
            'stage_class': TestingStage,
        },
    }
}
