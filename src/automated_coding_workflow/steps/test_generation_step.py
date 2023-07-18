"""
test_generation_step.py

This module contains the TestGenerationStep class, which represents the test generation step of the automated coding workflow.
"""
from src.workflow_types.types.base_step import BaseStep


class TestGenerationStep(BaseStep):
    """
    TestGenerationStep handles the processing of the response from the LLM API
    for the test generation step of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the test generation step.

        Returns:
            str: The constructed prompt for the test generation step.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the test generation step.

        Args:
            response (str): The LLM API response as a string.
        """
        # Process the response specific to the test generation step.
        pass  # Add test generation step-specific processing logic here.

    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
