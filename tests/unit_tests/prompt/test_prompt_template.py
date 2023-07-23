import pytest
from src.prompt.prompt_template import PromptTemplate
from src.prompt.prompt_template_variable import PromptTemplateVariable

def test_prompt_template_creation():
    """
    Given a template string and variables,
    When a PromptTemplate is created,
    Then it should correctly store its attributes.
    """
    variable = PromptTemplateVariable(name="requirement", 
                                      source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                      allow_code_context_building=True, 
                                      allow_llm_refinement=True)

    template_str = "This is a template with {requirement}"
    prompt_template = PromptTemplate(template=template_str, variables=[variable])

    assert prompt_template.template == template_str
    assert prompt_template.variables == [variable]

def test_prompt_template_to_dict():
    """
    Given a PromptTemplate,
    When its to_dict method is called,
    Then it should return a dictionary representation of the template.
    """
    variable = PromptTemplateVariable(name="requirement", 
                                      source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                      allow_code_context_building=True, 
                                      allow_llm_refinement=True)

    template_str = "This is a template with {requirement}"
    prompt_template = PromptTemplate(template=template_str, variables=[variable])

    expected_dict = {
        "template": template_str,
        "variables": [variable.to_dict()]
    }

    assert prompt_template.to_dict() == expected_dict
