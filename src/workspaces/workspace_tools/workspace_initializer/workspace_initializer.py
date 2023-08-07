# src/workspaces/workspace_tools/workspace_initializer/workspace_initializer.py

from .python_project_initializer import PythonProjectInitializer
from .react_project_initializer import ReactProjectInitializer
from .java_project_initializer import JavaProjectInitializer

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
