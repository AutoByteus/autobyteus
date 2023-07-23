"""
src/prompt/prompt_template.py

This module contains the PromptTemplate class, which represents a prompt that may contain various template variables.

PromptTemplate class features:
- The raw template string.
- A list of associated TemplateVariable instances.
- A method to convert the prompt template to a dictionary representation for frontend communication.
"""


from src.prompt.prompt_template_variable import PromptTemplateVariable


class PromptTemplate:
    def __init__(self, template: str, variables: list[PromptTemplateVariable]):
        self.template = template
        self.variables = variables

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
