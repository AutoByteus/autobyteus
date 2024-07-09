from autobyteus.prompt.prompt_template import PromptTemplate

class PromptBuilder:
    def __init__(self):
        self.template = None
        self.variable_values = {}

    @classmethod
    def with_template(cls, file_name: str) -> 'PromptBuilder':
        """
        Create a PromptBuilder instance with the specified template file.

        Args:
            file_name (str): The path to the template file.

        Returns:
            PromptBuilder: The PromptBuilder instance.
        """
        builder = cls()
        builder.template = PromptTemplate(file=file_name)
        return builder

    def variables(self, **kwargs) -> 'PromptBuilder':
        """
        Set the variable values for the prompt.

        Args:
            **kwargs: Keyword arguments representing variable names and their values.

        Returns:
            PromptBuilder: The PromptBuilder instance for method chaining.
        """
        self.variable_values.update(kwargs)
        return self

    def build(self) -> str:
        """
        Build the final prompt by filling the template with the set variable values.

        Returns:
            str: The final prompt.
        """
        if self.template is None:
            raise ValueError("Template is not set")
        return self.template.fill(self.variable_values)