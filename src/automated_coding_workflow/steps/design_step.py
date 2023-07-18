"""
src/automated_coding_workflow/design_stage.py

This module contains the DesignStep class, which represents the design stage of the automated coding workflow.
"""

from src.workflow_types.types.base_step import BaseStep

class DesignStep(BaseStep):
    """
    DesignStep is the class representing the design step of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the design step.

        Returns:
            str: The constructed prompt for the design step.
        """
        return "Please design the software architecture."

    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the design step.

        Args:
            response (str): The LLM API response as a string.
        """
        # Implement the processing of the response here.
        pass

    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
