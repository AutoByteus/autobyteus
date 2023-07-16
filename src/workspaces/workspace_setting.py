from src.workspaces.workspace_directory_tree import WorkspaceDirectoryTree


class WorkspaceSetting:
    """
    Class to store the parsed workspace structure and other related objects.
    """
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.directory_tree = None  # Added directory_tree attribute

    def set_directory_tree(self, directory_tree: WorkspaceDirectoryTree):
        """
        Set the directory tree of the workspace.

        Args:
            directory_tree (WorkspaceDirectoryTree): The directory tree of the workspace.
        """
        self.directory_tree = directory_tree  # Set directory_tree
