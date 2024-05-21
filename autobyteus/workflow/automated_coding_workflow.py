# autobyteus/automated_coding_workflow/automated_coding_workflow.py
"""
automated_coding_workflow.py: Contains the AutomatedCodingStep class, which represents the main entry point for running the automated coding workflow.
"""

import json
from typing import Dict, Optional
from autobyteus.llm.llm_registry import LLMIntegrationRegistry

from autobyteus.workflow.config import WORKFLOW_CONFIG
from autobyteus.workflow.types.base_step import BaseStep
from autobyteus.workflow.types.base_workflow import WorkflowStatus
from autobyteus.workflow.types.workflow_template_config import StepsTemplateConfig
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting

class AutomatedCodingWorkflow:
    """
    A class to represent and manage a fully automated coding workflow.

    The workflow is composed of multiple steps, each step represented as an instance of a class derived from BaseStep. Steps can have sub-steps, forming a potentially multi-level workflow.

    Attributes:
        workspace_setting (WorkspaceSetting): The settings associated with the workspace.
        steps (Dict[str, BaseStep]): A dictionary of step instances keyed by their step IDs.
        name (str): The name of the workflow. Default is "automated_coding_workflow".
        config (dict): The configuration details for the workflow. Loaded from `WORKFLOW_CONFIG`.
    """

    name = "automated_coding_workflow"
    config = WORKFLOW_CONFIG

    def __init__(self, workspace_setting: WorkspaceSetting): 
        """
        Initialize the AutomatedCodingWorkflow with the given workspace setting.

        Args:
            workspace_setting (WorkspaceSetting): The settings associated with the workspace.
        """
        self.workspace_setting = workspace_setting
        self.llm_integration_registry = LLMIntegrationRegistry()
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

    def to_json(self) -> str:
        """
        Converts the workflow instance to a JSON representation, including its steps.

        Returns:
            str: The JSON representation of the workflow instance.
        """
        workflow_data = {
            "name": self.name,
            "steps": {step_id: step.to_dict() for step_id, step in self.steps.items()}
        }

        return json.dumps(workflow_data)
    
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
