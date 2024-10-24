from autobyteus.prompt.prompt_template_variable import PromptTemplateVariable
import string

class SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, '{' + key + '}')
        else:
            return super().get_value(key, args, kwargs)

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
        Fill the template using the provided values. Only the variables specified in 'values' are replaced.
        Other placeholders remain unchanged.

        Args:
            values (dict): Dictionary containing variable names as keys and their respective values.

        Returns:
            str: The partially filled template string.
        """
        formatter = SafeFormatter()
        return formatter.format(self.template, **values)