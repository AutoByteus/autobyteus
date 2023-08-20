# tests/unit_tests/workflow_types/types/test_base_step.py

from src.workflow_types.types.base_step import BaseStep
from src.prompt.prompt_template import PromptTemplate
from src.prompt.prompt_template_variable import PromptTemplateVariable
from src.workflow_types.types.base_workflow import BaseWorkflow

# Mock class for testing purposes
class MockStep(BaseStep):
    name = "mock_step"
    prompt_template = PromptTemplate(
        template="This is a mock template with {variable1} and {variable2}",
        variables=[
            PromptTemplateVariable("variable1", PromptTemplateVariable.SOURCE_USER_INPUT, True, True),
            PromptTemplateVariable("variable2", PromptTemplateVariable.SOURCE_DYNAMIC, False, False)
        ]
    )
    
    def construct_prompt(self) -> str:
        return "Mock Prompt"

    def process_response(self, response: str) -> None:
        pass

    def execute(self) -> None:
        super().execute()

def test_to_dict_representation():
    """
    GIVEN: An instance of MockStep with realistic PromptTemplate and PromptTemplateVariable values
    WHEN: to_dict method is called
    THEN: It should return the correct dictionary representation of the MockStep instance.
    """
    mock_workflow = BaseWorkflow()  # Creating a mock workflow for instantiation
    step = MockStep(mock_workflow)
    result = step.to_dict()
    assert isinstance(result, dict)
    assert result["id"] == step.id
    assert result["name"] == step.name
    assert result["prompt_template"]["template"] == "This is a mock template with {variable1} and {variable2}"
    assert len(result["prompt_template"]["variables"]) == 2
    assert result["prompt_template"]["variables"][0]["name"] == "variable1"
