"""
This module defines the BaseTool interface which serves as a foundational contract for all tools.

Classes:
    BaseTool: An abstract class that other tool classes should implement.
"""


from abc import ABC, abstractmethod

class BaseTool(ABC):
    """
    An abstract base class that requires the implementation of an execute method.
    This is the core method all tools should provide.
    """
    @abstractmethod
    def execute(self, **kwargs):
        """Execute the tool's main functionality.

        Args:
            **kwargs: Keyword arguments that can be used to customize the tool's execution.
        """
        pass
