# src/workspaces/workspace_tools/workspace_initializer/project_initializer.py

from abc import ABC, abstractmethod

class BaseProjectInitializer(ABC):
    """
    Base class for all project initializers. It provides an interface
    that all concrete project initializers should implement.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for ProjectInitializer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be initialized.
        """
        self.workspace_setting = workspace_setting

    @abstractmethod
    def initialize(self):
        """
        Initialize the project.
        """
