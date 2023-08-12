# src/workspaces/workspace_tools/workspace_initializer/workspace_initializer.py

from src.workspaces.workspace_tools.base_workspace_tool import BaseWorkspaceTool
from src.workspaces.workspace_tools.workspace_initializer.java_project_initializer import JavaProjectInitializer
from src.workspaces.workspace_tools.workspace_initializer.python_project_initializer import PythonProjectInitializer
from src.workspaces.workspace_tools.workspace_initializer.react_project_initializer import ReactProjectInitializer


class WorkspaceInitializer(BaseWorkspaceTool):
    """
    Workspace Initializer class to set up default project structures 
    depending on the project type.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for WorkspaceInitializer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be initialized.
        """
        super().__init__(workspace_setting)

        if self.workspace_setting.project_type == "python":
            self.project_initializer = PythonProjectInitializer(workspace_setting)
        elif self.workspace_setting.project_type == "react":
            self.project_initializer = ReactProjectInitializer(workspace_setting)
        elif self.workspace_setting.project_type == "java":
            self.project_initializer = JavaProjectInitializer(workspace_setting)
        else:
            raise ValueError(f"Unsupported project type: {self.workspace_setting.project_type}")

    def execute(self):
        """
        Execute the initialization process on the workspace.
        """
        self.project_initializer.initialize()
