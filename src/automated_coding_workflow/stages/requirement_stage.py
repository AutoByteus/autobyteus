"""
requirement_stage.py

This module contains the RequirementStage class, derived from the Stage base class.
"""

from typing_extensions import override
from llm_workflow_core.types.base_stage import BaseStage

class RequirementStage(BaseStage):


    @override
    def construct_prompt(self) -> str:
        """
        Construct the prompt for the requirement stage.

        Returns:
            str: The constructed prompt for the requirement stage.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    @override
    def process_response(self, response: str):
        """
        Process the response for the Requirement stage.

        Args:
            response (str): The response from the LLM API.
        """
        # Implement the response processing logic specific to the Requirement stage

    def execute(self) -> None:
        """
        Execute the stage.

        This method should be implemented in derived classes to define the stage's execution logic.
        """
        print("not doing anything now")
