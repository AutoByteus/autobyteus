"""
Module: workspace_refactorer

This module provides the WorkspaceRefactorer class which is responsible for refactoring workspaces 
based on the project type. It delegates the actual refactoring logic to specific ProjectRefactorer 
classes, tailored to the unique requirements of each project type like Python, Java, or NodeJS.
"""

from src.llm_integrations.llm_integration_registry import LLMIntegrationRegistry
from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from src.workspaces.workspace_tools.workspace_refactorer.java_project_refactorer import JavaProjectRefactorer
from src.workspaces.workspace_tools.workspace_refactorer.nodejs_project_refactorer import NodeJSProjectRefactorer
from src.workspaces.workspace_tools.workspace_refactorer.python_project_refactorer import PythonProjectRefactorer


class WorkspaceRefactorer(BaseWorkspaceTool):
    name = "Refactorer"
    """
    Refactorer class to restructure and refactor the workspace based on the project type.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for WorkspaceRefactorer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be refactored.
        """
        super().__init__(workspace_setting)

        if self.workspace_setting.project_type == "python":
            self.project_refactorer = PythonProjectRefactorer(workspace_setting)
        elif self.workspace_setting.project_type == "java":
            self.project_refactorer = JavaProjectRefactorer(workspace_setting)
        elif self.workspace_setting.project_type == "nodejs":
            self.project_refactorer = NodeJSProjectRefactorer(workspace_setting)

    @property
    def prompt_template(self) -> str:
        """
        Fetch the prompt template from the specific project refactorer.

        Returns:
            str: The prompt template for the specific project type.
        """
        return self.project_refactorer.prompt_template

    def execute(self):
        """
        Execute the refactoring process on the workspace.
        """
        self.project_refactorer.refactor()
