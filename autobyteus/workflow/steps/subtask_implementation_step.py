from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.workflow.types.base_step import BaseStep


class SubtaskImplementationStep(BaseStep):
    name = "implementation"
    prompt_template = PromptTemplate(template="")


    """
    ImplementationStep handles the processing of the response from the LLM API
    for the implementation step of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the implementation step.

        Returns:
            str: The constructed prompt for the implementation step.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the implementation step.

        Args:
            response (str): The LLM API response as a string.
        """
        # Process the response specific to the implementation step.
        pass  # Add implementation step-specific processing logic here.

    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
