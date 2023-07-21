# src/semantic_code/requirement/requirement_step.py

"""
requirement_step.py

This module contains the RequirementStep class, derived from the Step base class.
"""

from typing_extensions import override
from src.workflow_types.types.base_step import BaseStep

class RequirementStep(BaseStep):
    name = "requirement"
    
    # Define the template string
    prompt_template = """
    As a senior Python software engineer, address the requriements outlined between the `$start$` and `$end$` tokens in the `[Requirement]` section.

    [Guidelines]
    - Use appropriate design patterns where neccessary.
    - Follow SOLID principles and Python's best coding practices.
    - Contemplate refactoring where necessary.
    - Follow python docstring best practices, ensuring each file begins with a file-level docstring.
    - Include file paths with their complete codes in code block in the output for easy copy paste. Do not use placeholders.
    - Explain whether to create a new folder or use an existing one for file placement. Use descriptive naming conventions for files and folders that correlate with the requirement's features. For context, the current project's file structure looks like this:
        - src
            - ...
            - semantic_code
                - embedding
                    - openai_embedding_creator.py
        - tests
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
                        
    - Always use absolute imports over relative ones.
    - Update docstrings in line with any code modifications.

    Think step by step.

    [Requirement]
    $start$
    {requirement}
    $end$
    """
    
    @override
    def construct_prompt(self, requirement: str) -> str:
        """
        Construct the prompt for the requirement step.

        Args:
            requirement (str): The requirement to be filled in the prompt_template.

        Returns:
            str: The constructed prompt for the requirement step.
        """
        # Format the prompt with the provided requirement
        prompt = self.prompt_template.format(requirement=requirement)
        return prompt
    
    @override
    def process_response(self, response: str):
        """
        Process the response for the Requirement step.

        Args:
            response (str): The response from the LLM API.
        """
        # Implement the response processing logic specific to the Requirement step
    
    @override
    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
