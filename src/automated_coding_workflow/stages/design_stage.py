"""
design_stage.py

This module contains the DesignStage class, which represents the design stage of the automated coding workflow.
"""

from llm_workflow_core.types.base_stage import BaseStage

class DesignStage(BaseStage):
    """
    DesignStage is the class representing the design stage of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the design stage.

        Returns:
            str: The constructed prompt for the design stage.
        """
        return "Please design the software architecture."

    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the design stage.

        Args:
            response (str): The LLM API response as a string.
        """
        # Implement the processing of the response here.
        pass

    def execute(self) -> None:
        """
        Execute the stage.

        This method should be implemented in derived classes to define the stage's execution logic.
        """
        print("not doing anything now")
