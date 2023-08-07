from src.workspaces.setting.workspace_setting import WorkspaceSetting
from src.prompt.prompt_template import PromptTemplate
from src.prompt.prompt_template_variable import PromptTemplateVariable


class FileRefactorer:
    """
    Class to refactor individual Python files.
    """

    # Define the PromptTemplateVariable
    file_path_variable = PromptTemplateVariable(name="file_path", 
                                                source=PromptTemplateVariable.SOURCE_USER_INPUT, 
                                                allow_code_context_building=True, 
                                                allow_llm_refinement=True)

    # Define the PromptTemplate
    prompt_template = PromptTemplate(
        template="""
        Please refactor the Python file at {file_path}.
        """,
        variables=[file_path_variable]
    )

    def __init__(self, file_path: str, workspace_setting: WorkspaceSetting):
        """
        Constructor for FileRefactorer.

        Args:
            file_path (str): The path of the file to be refactored.
            workspace_setting (WorkspaceSetting): The setting of the workspace.
        """
        self.file_path = file_path
        self.workspace_setting = workspace_setting

    def refactor(self):
        """
        Refactor the Python file.
        """
        # Construct the prompt
        prompt = self.construct_prompt()

        # Send the prompt to the LLM API and get the response
        # Assume the function send_prompt_to_llm exists and returns the response from the LLM API
        response = send_prompt_to_llm(prompt)

        # Process the response
        self.process_response(response)

    def construct_prompt(self):
        """
        Construct the prompt for the Python file refactoring.

        Returns:
            str: The constructed prompt for the Python file refactoring.
        """
        # Use the PromptTemplate's method to fill in the variable
        prompt = self.prompt_template.fill({"file_path": self.file_path})
        return prompt

    def process_response(self, response):
        """
        Process the response from the LLM API for the Python file refactoring.

        Args:
            response (str): The LLM API response as a string.
        """
        # Implement the processing of the response here
        # For example, we might write the updated code back to the file
        write_updated_code_to_file(self.file_path, response)
