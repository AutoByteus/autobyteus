import pytest
from autobyteus.prompt.prompt_template_variable import PromptTemplateVariable

def test_prompt_template_variable_creation_with_user_input():
    """
    Given a user input source,
    When a PromptTemplateVariable is created,
    Then it should correctly store its attributes.
    """
    variable = PromptTemplateVariable(name="requirement", 
                                      source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                      allow_code_context_building=True, 
                                      allow_llm_refinement=True)
    
    assert variable.name == "requirement"
    assert variable.source == PromptTemplateVariable.SOURCE_USER_INPUT
    assert variable.allow_code_context_building == True
    assert variable.allow_llm_refinement == True

def test_prompt_template_variable_to_dict():
    """
    Given a PromptTemplateVariable,
    When its to_dict method is called,
    Then it should return a dictionary representation of the variable.
    """
    variable = PromptTemplateVariable(name="requirement", 
                                      source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                      allow_code_context_building=True, 
                                      allow_llm_refinement=True)

    expected_dict = {
        "name": "requirement",
        "source": "USER_INPUT",
        "allow_code_context_building": True,
        "allow_llm_refinement": True
    }

    assert variable.to_dict() == expected_dict
