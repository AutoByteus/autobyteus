# file: autobyteus/prompt/prompt_template.py

from autobyteus.prompt.prompt_template_variable import PromptTemplateVariable

class PromptTemplate:
    def __init__(self, template: str = None, file: str = None, variables: list[PromptTemplateVariable] = None):
        if file is not None:
            with open(file, 'r') as f:
                self.template = f.read()
        elif template is not None:
            self.template = template
        else:
            raise ValueError("Either 'template' or 'file' must be provided.")

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
