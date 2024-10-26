import os
import pytest
from autobyteus.prompt.prompt_builder import PromptBuilder

@pytest.fixture
def template_file(tmp_path):
    template_content = "[Movie Title]:\n{{ movie_title }}\n\n[Genre]:\n{{ genre }}"
    template_file = tmp_path / "template.txt"
    with open(template_file, "w") as file:
        file.write(template_content)
    return template_file

def test_prompt_builder(template_file):
    # Test building a prompt with variables
    prompt = (
        PromptBuilder.from_file(str(template_file))
        .set_variable_value("movie_title", "The Matrix")
        .set_variable_value("genre", "Science Fiction")
        .build()
    )
    expected_prompt = "[Movie Title]:\nThe Matrix\n\n[Genre]:\nScience Fiction"
    assert prompt == expected_prompt

def test_prompt_builder_missing_template():
    # Test building a prompt without setting a template
    with pytest.raises(ValueError, match="Template is not set"):
        PromptBuilder().build()

def test_prompt_builder_missing_variable(template_file):
    # Test building a prompt with missing variables
    prompt = (
        PromptBuilder.from_file(str(template_file))
        .set_variable_value("movie_title", "Inception")
        .build()
    )
    expected_prompt = "[Movie Title]:\nInception\n\n[Genre]:\n"
    assert prompt == expected_prompt