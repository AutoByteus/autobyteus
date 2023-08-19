"""
Workspace Scaffolder Module.

This module provides the scaffolding logic for workspaces based on the type of project.
It determines the type of project and then applies the respective project scaffolder.
"""

from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from src.workspaces.workspace_tools.workspace_scaffolder.python_project_scaffolder import PythonProjectScaffolder
from src.workspaces.workspace_tools.workspace_scaffolder.react_project_scaffolder import ReactProjectScaffolder
from src.workspaces.workspace_tools.workspace_scaffolder.java_project_scaffolder import JavaProjectScaffolder

class WorkspaceScaffolder(BaseWorkspaceTool):
    """
    Workspace Scaffolder class to set up default project structures 
    depending on the project type.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for WorkspaceScaffolder.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be scaffolded.
        """
        super().__init__(workspace_setting)

        if self.workspace_setting.project_type == "python":
            self.project_scaffolder = PythonProjectScaffolder(workspace_setting)
        elif self.workspace_setting.project_type == "react":
            self.project_scaffolder = ReactProjectScaffolder(workspace_setting)
        elif self.workspace_setting.project_type == "java":
            self.project_scaffolder = JavaProjectScaffolder(workspace_setting)
        else:
            raise ValueError(f"Unsupported project type: {self.workspace_setting.project_type}")

    def execute(self):
        """
        Execute the scaffolding process on the workspace.
        """
        self.project_scaffolder.scaffold()
