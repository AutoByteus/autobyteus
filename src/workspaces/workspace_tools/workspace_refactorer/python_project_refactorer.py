from src.workspaces.setting.workspace_setting import WorkspaceSetting
from src.workspaces.workspace_tools.workspace_refactorer.base_project_refactorer import BaseProjectRefactorer
from src.workspaces.workspace_tools.workspace_refactorer.file_refactorer import FileRefactorer


class PythonProjectRefactorer(BaseProjectRefactorer):
    """
    Class to refactor Python projects.
    """

    def __init__(self, workspace_setting: WorkspaceSetting):
        """
        Constructor for PythonProjectRefactorer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be refactored.
        """
        self.workspace_setting: WorkspaceSetting = workspace_setting

    def refactor(self):
        """
        Refactor the Python project.

        This method iterates over each Python file in the src directory and refactors it individually.
        """
        # Use the directory_tree from workspace_setting
        directory_tree = self.workspace_setting.directory_tree

        # Iterate over each node in the directory tree
        for node in directory_tree.get_all_nodes():
            # If the node is a file and it's in the src directory and it's not an __init__.py file, refactor it
            if node.is_file and "src" in node.path and "__init__.py" not in node.path:
                file_refactorer = FileRefactorer(file_path=node.path, workspace_setting=self.workspace_setting)
                file_refactorer.refactor()

    def execute(self):
        """
        Execute the refactoring.

        This method calls the refactor method to execute the refactoring.
        """
        self.refactor()
