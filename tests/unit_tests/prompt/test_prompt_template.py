import json
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

    # Convert expected_dict to a formatted string
    expected_string = json.dumps(expected_dict, indent=4)

    assert json.dumps(prompt_template.to_dict(), indent=4) == expected_string

def test_prompt_template_variable_to_dict_representation():
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

def test_set_and_get_value_for_prompt_template_variable():
    """
    Given a PromptTemplateVariable,
    When a value is set using the set_value method,
    Then the get_value method should return the same value.
    """
    variable = PromptTemplateVariable(name="requirement", source=PromptTemplateVariable.SOURCE_USER_INPUT)
    variable.set_value("test_value")
    assert variable.get_value() == "test_value"

def test_get_value_without_setting_throws_error():
    """
    Given a PromptTemplateVariable without a set value,
    When the get_value method is called,
    Then it should raise a ValueError.
    """
    variable = PromptTemplateVariable(name="requirement", source=PromptTemplateVariable.SOURCE_USER_INPUT)
    with pytest.raises(ValueError, match="Value for variable 'requirement' is not set."):
        variable.get_value()
