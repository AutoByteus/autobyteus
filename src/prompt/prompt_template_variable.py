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
"""

class PromptTemplateVariable:
    SOURCE_DYNAMIC = "DYNAMIC"
    SOURCE_USER_INPUT = "USER_INPUT"

    def __init__(self, name: str, source: str, allow_code_context_building: bool = False, allow_llm_refinement: bool = False):
        self.name = name
        self.source = source
        self.allow_code_context_building = allow_code_context_building
        self.allow_llm_refinement = allow_llm_refinement

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
