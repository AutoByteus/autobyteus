"""
src/prompt/prompt_template.py

This module contains the PromptTemplate class, which represents a prompt that may contain various template variables.

PromptTemplate class features:
- The raw template string.
- A list of associated PromptTemplateVariable instances.
- A method to convert the prompt template to a dictionary representation for frontend communication.
"""

from src.prompt.prompt_template_variable import PromptTemplateVariable


class PromptTemplate:
    def __init__(self, template: str, variables: list[PromptTemplateVariable] = None):
        self.template = template
        self.variables = variables if variables is not None else []

    def to_dict(self) -> dict:
        """
        Converts the PromptTemplate instance to a dictionary representation.

        Returns:
            dict: Dictionary representation of the PromptTemplate instance.
        """
        return {
            "template": self.template,
            "variables": [variable.to_dict() for variable in self.variables]
        }
    
    def fill(self, values: dict) -> str:
        """
        Fill the template using the provided values.

        Args:
            values (dict): Dictionary containing variable names as keys and their respective values.

        Returns:
            str: The filled template string.
        
        Raises:
            KeyError: If a required variable is missing from the provided values.
        """
        try:
            return self.template.format(**values)
        except KeyError as e:
            raise KeyError(f"Missing value for template variable: {e}")

