from llm_workflow_core.types.base_stage import BaseStage

class TestingStage(BaseStage):
    """
    TestingStage handles the processing of the response from the LLM API
    for the testing stage of the automated coding workflow.
    """

    def construct_prompt(self) -> str:
        """
        Construct the prompt for the requirement stage.

        Returns:
            str: The constructed prompt for the requirement stage.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for the testing stage.

        Args:
            response (str): The LLM API response as a string.
        """
        # Process the response specific to the testing stage.
        pass  # Add testing stage-specific processing logic here.

    def execute(self) -> None:
        """
        Execute the stage.

        This method should be implemented in derived classes to define the stage's execution logic.
        """
        print("not doing anything now")
