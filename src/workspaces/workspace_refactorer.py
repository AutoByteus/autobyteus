from src.workspaces.workspace_tools.python_doc_refactor_task import PythonDocRefactorTask


class WorkspaceRefactorer:
    """
    The WorkspaceRefactorer class provides functionalities to refactor a given workspace.
    
    Attributes:
        workspace_path (str): The path to the workspace to be refactored.
    """

    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path

    def execute_refactor(self):
        project_type = self.determine_project_type()
        if project_type == "python":
            doc_refactor = PythonDocRefactorTask(self.workspace_path)
            doc_refactor.execute()

    def determine_project_type(self) -> str:
        return "python"