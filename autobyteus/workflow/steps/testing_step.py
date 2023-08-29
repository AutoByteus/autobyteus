from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.workflow.types.base_step import BaseStep


class TestingStep(BaseStep):
    name="run_test"
    prompt_template = PromptTemplate(template="")

    """
    TestingStep handles the processing of the response from the LLM API
    for the testing step of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the testing step.

        Returns:
            str: The constructed prompt for the testing step.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the testing step.

        Args:
            response (str): The LLM API response as a string.
        """
        # Process the response specific to the testing step.
        pass  # Add testing step-specific processing logic here.

    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
