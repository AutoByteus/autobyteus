"""
Module: workspace_refactorer

This module provides the WorkspaceRefactorer class which is responsible for refactoring workspaces 
based on the project type. It delegates the actual refactoring logic to specific ProjectRefactorer 
classes, tailored to the unique requirements of each project type like Python, Java, or NodeJS.
"""

from autobyteus.llm_integrations.llm_integration_registry import LLMIntegrationRegistry
from autobyteus.workspaces.setting.project_types import ProjectType
from autobyteus.workspaces.setting.workspace_setting import WorkspaceSetting
from autobyteus.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from autobyteus.workspaces.workspace_tools.workspace_refactorer.java_project_refactorer import JavaProjectRefactorer
from autobyteus.workspaces.workspace_tools.workspace_refactorer.nodejs_project_refactorer import NodeJSProjectRefactorer
from autobyteus.workspaces.workspace_tools.workspace_refactorer.python_project_refactorer import PythonProjectRefactorer


class WorkspaceRefactorer(BaseWorkspaceTool):
    """
    WorkspaceRefactorer is responsible for determining the appropriate project refactorer
    based on the workspace setting's project type.
    """
    
    # Mapping of project types to their respective refactorer classes
    REFACTORER_MAP = {
        ProjectType.PYTHON: PythonProjectRefactorer,
        ProjectType.JAVA: JavaProjectRefactorer,
        ProjectType.NODEJS: NodeJSProjectRefactorer
    }

    def __init__(self, workspace_setting: WorkspaceSetting):
        """
        Constructor for WorkspaceRefactorer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be refactored.
        """
        super().__init__(workspace_setting)

        # Find the appropriate refactorer class for the project type
        refactorer_class = self.REFACTORER_MAP.get(workspace_setting.project_type)

        if not refactorer_class:
            raise ValueError(f"Invalid project type: {workspace_setting.project_type}")

        self.project_refactorer = refactorer_class(workspace_setting)
        
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
