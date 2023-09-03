# autobyteus/workspaces/workspace_tools/workspace_refactorer/project_refactorer.py

from abc import ABC, abstractmethod

from autobyteus.prompt.prompt_template import PromptTemplate


class BaseProjectRefactorer(ABC):
    prompt_template: PromptTemplate = None
    """
    Base class for all project refactorers. It provides an interface
    that all concrete project refactorers should implement.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for ProjectRefactorer.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace to be refactored.
        """
        self.workspace_setting = workspace_setting

    @abstractmethod
    def refactor(self):
        """
        Refactor the project.
        """
