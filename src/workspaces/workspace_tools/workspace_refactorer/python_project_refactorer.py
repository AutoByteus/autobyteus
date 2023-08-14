"""
Module: python_project_refactorer

This module offers the PythonProjectRefactorer class which is tasked with refactoring Python projects.
It provides mechanisms to organize, structure, and refactor Python source code in alignment with 
best practices and standards specific to Python development.
"""
from src.llm_integrations.llm_integration_registry import LLMIntegrationRegistry
from src.prompt.prompt_template import PromptTemplate
from src.prompt.prompt_template_variable import PromptTemplateVariable
from src.source_code_tree.file_explorer.file_reader import FileReader
from src.workspaces.setting.workspace_setting import WorkspaceSetting
from src.workspaces.workspace_tools.workspace_refactorer.base_project_refactorer import BaseProjectRefactorer

class PythonProjectRefactorer(BaseProjectRefactorer):
    """
    Class to refactor Python projects.
    """
    
    file_path_variable = PromptTemplateVariable(name="file_path", 
                                           source=PromptTemplateVariable)
    source_code_variable = PromptTemplateVariable(name="source_code", 
                                           source=PromptTemplateVariable)
    # Define the prompt template string
    template_str = """
    You are a top python software engineer who creates maintainable and understandable codes. You are given a task located between '$start$' and '$end$' tokens in the `[Task]` section.

    [Criterias]
    - Follow python PEP8 best practices. Don't forget add or update file-level docstring
    - Include complete updated code in code block. Do not use placeholders.

    Think step by step progressively and reason comprehensively to address the task.

    [Task]
    $start$
    Please examine the source code in file {file_path}
    ```
    {source_code}
    ```
    $end$
    """

    # Define the class-level prompt_template
    prompt_template: PromptTemplate = PromptTemplate(template=template_str, variables=[file_path_variable, source_code_variable])

    def __init__(self, workspace_setting: WorkspaceSetting):
        """
        Constructor for PythonProjectRefactorer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be refactored.
        """
        self.workspace_setting: WorkspaceSetting = workspace_setting
        self.llm_integration = LLMIntegrationRegistry().get('GPT4')

    def refactor(self):
        """
        Refactor the Python project.

        This method iterates over each Python file in the src directory and sends a prompt for refactoring to LLM.
        """
        directory_tree = self.workspace_setting.directory_tree

        for node in directory_tree.get_all_nodes():
            if node.is_file and "src" in node.path and "__init__.py" not in node.path:
                prompt = self.construct_prompt(node.path)
                response = self.llm_integration.process_input_messages(prompt)
                print(f"Refactoring suggestions for {node.path}:\n{response}")

    def construct_prompt(self, file_path: str):
        """
        Construct the prompt for the Python file refactoring.

        Args:
            file_path (str): The path to the Python file.

        Returns:
            str: The constructed prompt for the Python file refactoring.
        """
        source_code = FileReader.read_file(file_path)
        prompt = self.prompt_template.fill({"file_path": file_path, "source_code": source_code})
        return prompt
