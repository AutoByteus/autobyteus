"""
requirement_step.py

This module contains the RequirementStep class, derived from the Step base class.
"""

from typing_extensions import override
from src.workflow_types.types.base_step import BaseStep

class RequirementStep(BaseStep):
    name = "Refine And Enhance Task Description"
    prompt_template = '''The task name is {}. In this task, you will perform as an expert in refining and enhancing task descriptions. Your task is to analyze the provided task description given in "Task Description" section, improve it based on your domain and knowledge of doing similar task, and ensure the revised description better conveys its purpose while maintaining a professional and explicit writing style.

    Adjust the wording, add additional content or requirements as needed, drawing from your knowledge of similar features, and create a logically coherent and semantically organized output without redundancy.

    You should incorporate all information, including codes, from the original task description in the output, as it will be stored in a third-party platform for later reference. 

    For instance, if you recognize file paths and codes in the task description, you should extract the codes to the 'Code References' section, and put them under the respective path, description, and code subsections. Identify constraints such as programming languages, frameworks etc from the task description and include them in the 'Constraints' section.

    Use the following format for the output:

    ```Title: [Title of the task]

    Objective:
    - [Objective of the task]

    Background:
    - [Background information related to the task]

    Requirements:
    - [List of requirements for the task]

    Constraints:
    - [List of constraints or limitations for the task]

    Code References: (if codes exist in the task description)
    - path
    - description
    - code (complete code for the file given in the task description)
    ```

    Provide the complete output in a copiable preformatted text block.

    Task description:

    ```
    {}
    ```
    '''
    
    @override
    def construct_prompt(self) -> str:
        """
        Construct the prompt for the requirement step.

        Returns:
            str: The constructed prompt for the requirement step.
        """
        prompt = "Please provide the requirements for the project:"
        return prompt
    
    @override
    def process_response(self, response: str):
        """
        Process the response for the Requirement step.

        Args:
            response (str): The response from the LLM API.
        """
        # Implement the response processing logic specific to the Requirement step

    def execute(self) -> None:
        """
        Execute the step.

        This method should be implemented in derived classes to define the step's execution logic.
        """
        print("not doing anything now")
