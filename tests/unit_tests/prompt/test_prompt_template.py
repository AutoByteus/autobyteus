import json
import pytest
from autobyteus.prompt.prompt_template import PromptTemplate

def test_prompt_template_creation():
    """
    Given a template string,
    When a PromptTemplate is created,
    Then it should correctly store its attributes.
    """
    template_str = "This is a template with {{ requirement }}"
    prompt_template = PromptTemplate(template=template_str)

    assert prompt_template.template == template_str

def test_prompt_template_to_dict():
    """
    Given a PromptTemplate,
    When its to_dict method is called,
    Then it should return a dictionary representation of the template.
    """
    template_str = "This is a template with {{ requirement }}"
    prompt_template = PromptTemplate(template=template_str)

    expected_dict = {
        "template": template_str
    }

    # Convert expected_dict to a formatted string
    expected_string = json.dumps(expected_dict, indent=4)

    assert json.dumps(prompt_template.to_dict(), indent=4) == expected_string

def test_prompt_template_fill_with_all_variables():
    """
    Given a PromptTemplate and all required variables,
    When fill is called with the variables,
    Then it should return the correctly rendered template.
    """
    template_str = "Hello, {{ name }}! Welcome to {{ platform }}."
    prompt_template = PromptTemplate(template=template_str)
    filled = prompt_template.fill({"name": "Alice", "platform": "OpenAI"})
    expected = "Hello, Alice! Welcome to OpenAI."
    assert filled == expected

def test_prompt_template_fill_with_missing_variables():
    """
    Given a PromptTemplate with some variables,
    When fill is called with missing variables,
    Then the missing variables should be rendered as empty strings.
    """
    template_str = "Hello, {{ name }}! Welcome to {{ platform }}."
    prompt_template = PromptTemplate(template=template_str)
    filled = prompt_template.fill({"name": "Bob"})
    expected = "Hello, Bob! Welcome to ."
    assert filled == expected

def test_prompt_template_fill_with_extra_variables():
    """
    Given a PromptTemplate,
    When fill is called with extra variables,
    Then the extra variables should be ignored.
    """
    template_str = "Hello, {{ name }}!"
    prompt_template = PromptTemplate(template=template_str)
    filled = prompt_template.fill({"name": "Charlie", "platform": "OpenAI"})
    expected = "Hello, Charlie!"
    assert filled == expected