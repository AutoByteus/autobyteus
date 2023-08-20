"""
config.py
The WORKFLOW_CONFIG dictionary defines the structure of the workflow, including steps and substeps.
Each step is defined as a key-value pair, where the key is the step name and the value is a dictionary containing:
    - 'step_class': The class representing the step.
    - 'steps': A dictionary of substeps, if any, following the same structure.

For example, the 'requirement_step' has a 'refine' substep with its own class.
"""

from autobyteus.automated_coding_workflow.steps.requirement_step import RequirementStep
from autobyteus.automated_coding_workflow.steps.design_step import DesignStep
from autobyteus.automated_coding_workflow.steps.test_generation_step import TestGenerationStep
from autobyteus.automated_coding_workflow.steps.implementation_step import ImplementationStep
from autobyteus.automated_coding_workflow.steps.testing_step import TestingStep
from autobyteus.workflow_types.types.workflow_template_config import WorkflowTemplateStepsConfig

WORKFLOW_CONFIG: WorkflowTemplateStepsConfig = {
    'steps': {
        'requirement_step': {
            'step_class': RequirementStep,
            'steps': {
                'refine': {
                    'step_class': RequirementRefineStep
                }
            },
        },
        'design_step': {
            'step_class': DesignStep,
        },
        'test_generation_step': {
            'step_class': TestGenerationStep,
        },
        'implementation_step': {
            'step_class': ImplementationStep,
        },
        'testing_step': {
            'step_class': TestingStep,
        },
    }
}
