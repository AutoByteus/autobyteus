from autobyteus.prompt.prompt_template import PromptTemplate

class PromptBuilder:
    def __init__(self):
        self.template = None
        self.variable_values = {}

    @classmethod
    def from_file(cls, file_path: str) -> 'PromptBuilder':
        """
        Create a PromptBuilder instance with the specified template file.

        Args:
            file_path (str): The path to the template file.

        Returns:
            PromptBuilder: The PromptBuilder instance.
        """
        builder = cls()
        builder.template = PromptTemplate(file=file_path)
        return builder

    @classmethod
    def from_string(cls, template_string: str) -> 'PromptBuilder':
        """
        Create a PromptBuilder instance with the specified template string.

        Args:
            template_string (str): The template string.

        Returns:
            PromptBuilder: The PromptBuilder instance.
        """
        builder = cls()
        builder.template = PromptTemplate(template=template_string)
        return builder

    def set_variable_value(self, name: str, value: str) -> 'PromptBuilder':
        """
        Set the value for a specific variable in the prompt.

        Args:
            name (str): The name of the variable.
            value (str): The value to set for the variable.

        Returns:
            PromptBuilder: The PromptBuilder instance for method chaining.
        """
        self.variable_values[name] = value
        return self

    def build(self) -> str:
        """
        Build the final prompt by filling the template with the set variable values.

        Returns:
            str: The final prompt.

        Raises:
            ValueError: If the template is not set.
        """
        if self.template is None:
            raise ValueError("Template is not set")
        return self.template.fill(self.variable_values)