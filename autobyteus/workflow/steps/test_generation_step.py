"""
test_generation_step.py

This module contains the TestGenerationStep class, which represents the test generation step of the automated coding workflow.
"""
from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.prompt.prompt_template_variable import PromptTemplateVariable
from autobyteus.workflow_types.types.base_step import BaseStep


class TestGenerationStep(BaseStep):
    name = "generate_test"
   # Define the PromptTemplateVariable
    code_variable = PromptTemplateVariable(name="code", 
                                           source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                           allow_code_context_building=True, 
                                           allow_llm_refinement=False)

    # Define the PromptTemplate
    prompt_template = PromptTemplate(
        template="""
        You are a senior Python software engineer. You have been given a Python code file provided in the `[Code]` section. Your task is to create integration for the given Python code file.

        [Criteria]
        - Ensure that the test cases follow pytest best practices.
        - Create the test file path to follow the same practice used in the current project's test files structure:
            src
                - ...
                - semantic_code
                    - embedding
                        - openai_embedding_creator.py
            tests
                - unit_tests
                    - ...
                    - semantic_code
                        - embedding
                            - test_openai_embedding_creator.py
                - integration_tests
                    - ...
                    - semantic_code
                        - index
                            - test_index_service_integration.py

        - Ensure that the tests provide full coverage of the code.
        - Use behavior-driven naming conventions for the test cases.

        [Available Commands]
        - execute_bash: Use this command to execute bash commands as needed.
        - write_file: Use this command to write the test cases to a file.

        Think and reason yourself in high detail to address the task.


        [Code]
        {code}
        """,
        variables=[code_variable]
    )
    
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
