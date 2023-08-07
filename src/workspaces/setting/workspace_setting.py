# src/workspaces/setting/workspace_setting.py

class WorkspaceSetting:
    """
    Class to store the parsed workspace structure and other related objects.
    """
    def __init__(self, root_path: str, project_type: str):
        """
        Initialize a WorkspaceSetting.

        Args:
            root_path (str): The root path of the workspace.
            project_type (str): The type of the project.
        """
        self.root_path = root_path
        self.project_type = project_type
        self.directory_tree = None

    # Rest of the class...

    @property
    def project_type(self) -> str:
        """
        Get the type of the project.

        Returns:
            str: The type of the project.
        """
        return self._project_type

    @project_type.setter
    def project_type(self, value: str):
        """
        Set the type of the project.

        Args:
            value (str): The type of the project.
        """
        self._project_type = value

    def set_directory_tree(self, directory_tree: WorkspaceDirectoryTree):
        """
        Set the directory tree of the workspace.

        Args:
            directory_tree (WorkspaceDirectoryTree): The directory tree of the workspace.
        """
        self.directory_tree = directory_tree  # Set directory_tree


