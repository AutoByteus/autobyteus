"""
base_stage.py

This module contains the BaseStage class, which serves as an abstract base class for all stages in the automated coding
workflow. Each stage in the workflow should inherit from this class and implement the required methods. The BaseStage
class provides a foundation for creating custom stages with unique IDs, names, and prompt construction.

BaseStage class features:
- Unique ID generation for each stage instance.
- A class attribute for the stage name.
- Abstract methods for constructing prompts and processing responses that need to be implemented in derived classes.
- A method called execute for triggering the stage's execution, which needs to be implemented in derived classes.

To create a new stage, inherit from the BaseStage class, set the stage name using the set_stage_name class method,
and implement the required abstract methods and the execute method.
"""


from abc import ABC, abstractmethod
from llm_workflow_core.types.base_workflow import BaseWorkflow
from llm_workflow_core.utils.unique_id_generator import UniqueIDGenerator


class BaseStage(ABC):
    """
    BaseStage is the abstract base class for all stages in the automated coding workflow.
    Each stage should inherit from this class and implement the required methods.
    """

    name = None

    def __init__(self, workflow: BaseWorkflow):
        self.id = UniqueIDGenerator.generate_id()
        self.prompt = self.construct_prompt()
        self.workflow = workflow

    @classmethod
    def set_stage_name(cls, name: str):
        cls.name = name

    @abstractmethod
    def construct_prompt(self) -> str:
        """
        Construct the prompt for this stage.

        Returns:
            str: The constructed prompt for this stage.
        """
        pass

    @abstractmethod
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for this stage.

        Args:
            response (str): The LLM API response as a string.
        """
        pass

    @abstractmethod
    def execute(self) -> None:
        """
        Execute the stage.

        This method should be implemented in derived classes to define the stage's execution logic.
        """
        raise NotImplementedError("Derived classes must implement the execute method.")

