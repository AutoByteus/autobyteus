# autobyteus/workflow/steps/requirement_step.py

"""
requirement_step.py

This module contains the RequirementStep class, derived from the Step base class.
"""

from abc import abstractmethod
from typing_extensions import override
from autobyteus.prompt.prompt_template import PromptTemplate
from autobyteus.prompt.prompt_template_variable import PromptTemplateVariable
from autobyteus.workflow.types.base_step import BaseStep

class RequirementStep(BaseStep):
    name = "requirement"
    
    # Define the PromptTemplateVariable
    requirement_variable = PromptTemplateVariable(name="requirement", 
                                                  source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                                  allow_code_context_building=True, 
                                                  allow_llm_refinement=True)

    # Define the PromptTemplate
    prompt_template = PromptTemplate(
        template="""
        As the best Python software engineer on earth, address the requriements outlined between the `$start$` and `$end$` tokens in the `[Requirement]` section.
        [Guidelines]
        - Use appropriate design patterns where neccessary.
        - Follow SOLID principles and Python's best coding practices.
        - Consider refactoring where necessary.
        - Follow python docstring best practices, ensuring each file begins with a file-level docstring.
        - Include file paths with their complete codes in code block in the output, so i can easily copy and paste. Do not use placeholders.
        - Explain whether to create a new folder or use an existing one for file placement. Use descriptive naming conventions for files and folders that correlate with the requirement's features. For context, 
            the current project's file structure looks like this:
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

    Think step by step, and reason comphrehensively to address the task.
    [Requirement]
    $start$
    {requirement}
    $end$
    """,
        variables=[requirement_variable]
    )
    
    @override
    def construct_prompt(self, requirement: str) -> str:
        """
        Construct the prompt for the requirement step.

        Args:
            requirement (str): The requirement to be filled in the prompt_template.

        Returns:
            str: The constructed prompt for the requirement step.
        """
        # Use the PromptTemplate's method to fill in the variable
        prompt = self.prompt_template.fill({"requirement": requirement})
        return prompt
    
    def process_response(self, response: str) -> None:
        """
        Process the response from the LLM API for this step.

        Args:
            response (str): The LLM API response as a string.
        """
        raise NotImplementedError("Derived classes must implement the execute method.")


    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        raise NotImplementedError("Derived classes must implement the execute method.")












