from abc import ABC, abstractmethod

from src.workspaces.setting.workspace_setting import WorkspaceSetting

class BaseWorkspaceTool(ABC):
    """
    BaseWorkspaceTool is the abstract base class for all workspace-specific tools.
    Each tool should inherit from this class, provide a unique name, and implement the required methods.
    """
    name = None  # Name of the tool, should be overridden in subclasses
    _all_tools = []  # List to keep track of all tools

    def __init__(self, workspace_setting: WorkspaceSetting):
        """
        Constructor for BaseWorkspaceTool.

        Args:
            workspace_setting (WorkspaceSetting): The setting of the workspace.
        """
        self.workspace_setting = workspace_setting

    def __init_subclass__(cls, **kwargs):
        """
        Automatically called when a subclass is defined. Used to register the tool.
        """
        super().__init_subclass__(**kwargs)
        if cls.name:
            BaseWorkspaceTool._all_tools.append(cls.name)

    @classmethod
    def get_all_tools(cls):
        """
        Fetch names of all available tools.

        Returns:
            list: List containing names of all available workspace tools.
        """
        return cls._all_tools

    @abstractmethod
    def execute(self):
        """
        Execute the tool's main functionality. This method should be implemented by subclasses.
        
        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError("This method should be implemented by subclasses.")
