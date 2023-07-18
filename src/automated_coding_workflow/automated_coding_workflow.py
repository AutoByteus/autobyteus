"""
automated_coding_workflow.py: Contains the AutomatedCodingStep class, which represents the main entry point for running the automated coding workflow.
"""

from typing import Dict, Optional
from src.automated_coding_workflow.config import WORKFLOW_CONFIG
from src.llm_integrations.base_llm_integration import BaseLLMIntegration
from src.llm_integrations.llm_factory import create_llm_integration
from src.workflow_types.types.base_step import BaseStep
from src.workflow_types.types.workflow_status import WorkflowStatus
from src.workflow_types.types.workflow_template_config import StepsTemplateConfig

class AutomatedCodingWorkflow:
    """
    A class to represent and manage a fully automated coding workflow.

    The workflow is composed of multiple steps, each step represented as an instance of a class derived from BaseStep. Steps can have sub-steps, forming a potentially multi-level workflow.

    Attributes:
        steps (Dict[str, BaseStep]): A dictionary of step instances keyed by their step IDs.
        name (str): The name of the workflow. Default is "automated_coding_workflow".
        config (dict): The configuration details for the workflow. Loaded from `WORKFLOW_CONFIG`.
    """

    name = "automated_coding_workflow"
    config = WORKFLOW_CONFIG
    workspace_path = None

    def __init__(self):
        self.llm_integration = create_llm_integration()
        self.steps: Dict[str, BaseStep] = {}
        self._initialize_steps(AutomatedCodingWorkflow.config['steps'])

    def _initialize_steps(self, steps_config: Dict[str, StepsTemplateConfig]):
        """
        Initializes the steps of the workflow from a given configuration.

        If a step has sub-steps, it recursively initializes those as well.

        :param steps_config: A dictionary containing step configuration.
        """
        for step_id, step_config in steps_config.items():
            step_class = step_config['step_class']
            step_instance: BaseStep = step_class(self)
            self.steps[step_id] = step_instance

            if 'steps' in step_config:
                self._initialize_steps(step_config['steps'])

    def execute_step(self, step_id: str) -> Optional[str]:
        """
        Execute a specific step within the workflow using its ID.

        :param step_id: The ID of the step to execute.
        :return: The step result or None if the step_id is invalid.
        :raises ValueError: If the provided step_id is invalid.
        """
        step = self.steps.get(step_id)
        if step:
            return step.execute()
        else:
            raise ValueError(f"Invalid step_id: {step_id}")


    def start_workflow(self):
        """
        Set the status of the workflow to Started and raise a NotImplementedError for derived classes to implement.
        """
        self.status = WorkflowStatus.Started
