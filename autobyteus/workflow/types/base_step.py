"""
autobyteus/workflow/types/base_step.py

This module contains the BaseStep class, which serves as an abstract base class for all steps in the automated coding
workflow. Each step in the workflow should inherit from this class, implement the required methods, and provide versioning
capabilities through the PromptVersioningMixin. The BaseStep class provides a foundation for creating custom steps with 
unique IDs, names, dynamic prompt construction, and version management.

BaseStep class features:
- Unique ID generation for each step instance.
- A class attribute for the step name.
- Abstract methods for constructing prompts and processing responses that need to be implemented in derived classes.
- A method called execute for triggering the step's execution, which needs to be implemented in derived classes.
- Versioning capabilities for managing different prompt versions.

To create a new step, inherit from the BaseStep class, set the step name using the set_step_name class method,
implement the required abstract methods, the execute method, and provide a default_prompt for versioning.
"""

from abc import ABC, abstractmethod
from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.prompt.prompt_versioning_mixin import PromptVersioningMixin
from autobyteus.workflow.types.base_workflow import BaseWorkflow
from autobyteus.workflow.utils.unique_id_generator import UniqueIDGenerator


class BaseStep(ABC, PromptVersioningMixin):
    """
    BaseStep is the abstract base class for all steps in the automated coding workflow.
    Each step should inherit from this class, implement the required methods, and offer versioning capabilities.
    """

    name = None

    def __init__(self, workflow: BaseWorkflow):
        super().__init__()
        self.id = UniqueIDGenerator.generate_id()
        self.workflow = workflow
        self.default_prompt = self.construct_prompt()  # Assuming the default prompt is constructed using this method

    def to_dict(self) -> dict:
        """
        Converts the BaseStep instance to a dictionary representation.

        Returns:
            dict: Dictionary representation of the BaseStep instance.
        """
        return {
            "id": self.id,
            "name": self.name,
            "prompt_template": self.prompt_template.to_dict() if self.prompt_template else None,
            "current_version": self.load_latest_version()  # Load the current version of the prompt
        }

    def construct_prompt(self) -> str:
        """
        Construct the prompt for this step using the versioning system. If no version is available in the database,
        it falls back to the default prompt provided by the step.

        Returns:
            str: The constructed prompt for this step.
        """
        current_prompt_version = self.load_latest_version()
        if not current_prompt_version:
            return self.default_prompt
        return current_prompt_version.prompt_content

    @abstractmethod
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for this step.

        Args:
            response (str): The LLM API response as a string.
        """
        pass

    @abstractmethod
    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        raise NotImplementedError("Derived classes must implement the execute method.")
