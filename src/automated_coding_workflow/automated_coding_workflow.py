"""
automated_coding_workflow.py: Contains the AutomatedCodingWorkflow class, which represents the main entry point for running the automated coding workflow.
"""

from typing import Dict, Optional
from src.automated_coding_workflow.config import WORKFLOW_CONFIG
from src.llm_integrations.base_llm_integration import BaseLLMIntegration
from src.llm_integrations.llm_factory import create_llm_integration
from src.workflow_types.types.base_stage import BaseStage
from src.workflow_types.types.workflow_status import WorkflowStatus
from src.workflow_types.types.workflow_template_config import StageTemplateConfig


class AutomatedCodingWorkflow:
    """
    A class to represent and manage a fully automated coding workflow.

    The workflow is composed of multiple stages, each stage represented as an instance of a class derived from BaseStage. Stages can have sub-stages, forming a potentially multi-level workflow.

    Attributes:
        stages (Dict[str, BaseStage]): A dictionary of stage instances keyed by their stage IDs.
        name (str): The name of the workflow. Default is "automated_coding_workflow".
        config (dict): The configuration details for the workflow. Loaded from `WORKFLOW_CONFIG`.
    """

    name = "automated_coding_workflow"
    config = WORKFLOW_CONFIG
    workspace_path = None

    def __init__(self):
        self.llm_integration = create_llm_integration()
        self.stages: Dict[str, BaseStage] = {}
        self._initialize_stages(AutomatedCodingWorkflow.config['stages'])

    def _initialize_stages(self, stages_config: Dict[str, StageTemplateConfig]):
        """
        Initializes the stages of the workflow from a given configuration.

        If a stage has sub-stages, it recursively initializes those as well.

        :param stages_config: A dictionary containing stage configuration.
        """
        for stage_id, stage_config in stages_config.items():
            stage_class = stage_config['stage_class']
            stage_instance:BaseStage = stage_class(self)
            self.stages[stage_id] = stage_instance

            if 'stages' in stage_config:
                self._initialize_stages(stage_config['stages'])

    def execute_stage(self, stage_id: str) -> Optional[str]:
        """
        Execute a specific stage within the workflow using its ID.

        :param stage_id: The ID of the stage to execute.
        :return: The stage result or None if the stage_id is invalid.
        :raises ValueError: If the provided stage_id is invalid.
        """
        stage = self.stages.get(stage_id)
        if stage:
            return stage.execute()
        else:
            raise ValueError(f"Invalid stage_id: {stage_id}")


    def start_workflow(self):
        """
        Set the status of the workflow to Started and raise a NotImplementedError for derived classes to implement.
        """
        self.status = WorkflowStatus.Started
