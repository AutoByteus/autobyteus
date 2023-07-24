"""
src/prompt/prompt_template_variable.py

This module contains the PromptTemplateVariable class, which represents a variable within a prompt template. 
Each variable can have a source (e.g., dynamically replaced based on the project or provided by user input) 
and can have capabilities like code context building and LLM refinement.

PromptTemplateVariable class features:
- The variable name.
- The source of the variable: DYNAMIC or USER_INPUT.
- Flags to indicate if the variable allows code context building or LLM refinement.
- A method to convert the variable to a dictionary representation for frontend communication.
- Methods to set and retrieve the value of the variable.
"""

class PromptTemplateVariable:
    SOURCE_DYNAMIC = "DYNAMIC"
    SOURCE_USER_INPUT = "USER_INPUT"

    def __init__(self, name: str, source: str, allow_code_context_building: bool = False, allow_llm_refinement: bool = False):
        self.name = name
        self.source = source
        self.allow_code_context_building = allow_code_context_building
        self.allow_llm_refinement = allow_llm_refinement
        self._value = None  # Internal value storage

    def set_value(self, value: str) -> None:
        """
        Set the value for this variable.

        Args:
            value (str): The value to set.
        """
        self._value = value

    def get_value(self) -> str:
        """
        Retrieve the value for this variable.

        Returns:
            str: The value of this variable.
        
        Raises:
            ValueError: If the value is not set.
        """
        if self._value is None:
            raise ValueError(f"Value for variable '{self.name}' is not set.")
        return self._value

    def to_dict(self) -> dict:
        """
        Converts the PromptTemplateVariable instance to a dictionary representation.

        Returns:
            dict: Dictionary representation of the PromptTemplateVariable instance.
        """
        return {
            "name": self.name,
            "source": self.source,
            "allow_code_context_building": self.allow_code_context_building,
            "allow_llm_refinement": self.allow_llm_refinement
        }
