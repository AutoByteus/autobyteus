"""
base_workflow.py: Provides a BaseWorkflow class to be used as a base class for custom workflows.

The BaseWorkflow class offers a foundation for creating custom workflows with unique IDs, status, and configuration. It also supports optional LLM integration and allows to optionally set the configuration when initializing an instance.
"""

from enum import Enum
from src.llm_integrations.base_llm_integration import BaseLLMIntegration

from src.workflow_types.types.workflow_template_config import WorkflowTemplateStagesConfig
from src.workflow_types.utils.unique_id_generator import UniqueIDGenerator

class WorkflowStatus(Enum):
    """
    Enumeration representing the status of a workflow.
    """
    Success = 'Success'
    Started = 'Started'
    Failure = 'Failure'


class BaseWorkflow:
    """
    A base class for custom workflows with unique IDs, status, and optional configuration. Supports optional LLM integration.
    """

    name = None
    config = None

    def __init__(self, config: WorkflowTemplateStagesConfig = None, llm_integration: BaseLLMIntegration = None):
        """
        Initialize a BaseWorkflow instance with a unique ID, status, and optional configuration. Optionally accepts an LLM integration.

        :param config: (optional) The configuration for the workflow.
        :type config: WorkflowTemplateStagesConfig, optional
        :param llm_integration: An instance of a subclass of BaseLLMIntegration to be used for LLM integration, defaults to None.
        :type llm_integration: BaseLLMIntegration, optional
        """
        self.id = UniqueIDGenerator.generate_id()
        self.status = None
        self.llm_integration = llm_integration
        if config is not None:
            self.set_workflow_config(config)

    @classmethod
    def set_workflow_name(cls, name: str):
        cls.name = name

    @classmethod
    def set_workflow_config(cls, config: WorkflowTemplateStagesConfig):
        cls.config = config

    def get_workflow_status(self):
        """
        Get the current status of the workflow.

        Returns:
            WorkflowStatus: The current status of the workflow.
        """
        return self.status

    def start_workflow(self):
        """
        Set the status of the workflow to Started and raise a NotImplementedError for derived classes to implement.
        """
        self.status = WorkflowStatus.Started
        raise NotImplementedError("start_workflow method must be implemented in derived classes")

    def execute_stage(self, stage_config: dict):
        """
        Execute a stage in the workflow and raise a NotImplementedError for derived classes to implement.

        Args:
            stage_config (dict): The configuration of the stage to be executed.
        """
        raise NotImplementedError("execute_stage method must be implemented in derived classes")
