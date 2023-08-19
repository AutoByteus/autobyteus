"""
Workspace Scaffolder Module.

This module provides the base class for scaffolding projects within a workspace.
It is responsible for creating project template files when initializing a new project.
"""

from abc import ABC, abstractmethod

class BaseProjectScaffolder(ABC):
    """
    Base class for all project scaffolders within a workspace.
    
    This class provides an interface that all concrete project scaffolders should implement.
    It aids in the creation of project template files when a new project is being set up.
    """

    def __init__(self, workspace_setting):
        """
        Constructor for BaseProjectScaffolder.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace where the project is to be scaffolded.
        """
        self.workspace_setting = workspace_setting

    @abstractmethod
    def scaffold(self):
        """
        Scaffold the project within the specified workspace.
        
        This method should be overridden by concrete implementations to provide
        the actual scaffolding logic.
        """
