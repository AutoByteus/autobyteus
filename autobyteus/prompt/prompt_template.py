from jinja2 import Template, Environment, meta
import os

class PromptTemplate:
    def __init__(self, template: str = None, file: str = None):
        if file is not None:
            if not os.path.isfile(file):
                raise FileNotFoundError(f"Template file '{file}' does not exist.")
            with open(file, 'r') as f:
                self.template = f.read()
        elif template is not None:
            self.template = template
        else:
            raise ValueError("Either 'template' or 'file' must be provided.")

        # Initialize Jinja2 environment
        self.env = Environment()
        self.parsed_content = self.env.parse(self.template)
        self.required_vars = meta.find_undeclared_variables(self.parsed_content)

    def to_dict(self) -> dict:
        """
        Converts the PromptTemplate instance to a dictionary representation.

        Returns:
            dict: Dictionary representation of the PromptTemplate instance.
        """
        return {
            "template": self.template
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
        template = Template(self.template)
        return template.render(**values)