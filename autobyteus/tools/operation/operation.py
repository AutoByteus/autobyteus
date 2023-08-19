
"""
path: tools/operation/operation.py
This module defines the base Operation class that serves as a blueprint for all operations.
Each operation can be executed, undone, and serialized to and from a dictionary format.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type


class Operation(ABC):
    """
    Base Operation class that provides a template for all operations.
    
    Attributes:
    - None defined for the base class.
    
    Methods:
    - execute: Executes the operation.
    - undo: Undoes the operation.
    - to_dict: Serializes the operation to a dictionary.
    - from_dict: Deserializes the operation from a dictionary.
    """
    
    @abstractmethod
    def execute(self) -> None:
        """
        Execute the operation. 
        This method should be overridden by subclasses to provide specific execution logic.
        """
        pass

    @abstractmethod
    def undo(self) -> None:
        """
        Undo the operation.
        This method should be overridden by subclasses to provide specific undo logic.
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict:
        """
        Serialize the operation to a dictionary format.
        
        Returns:
            Dict: A dictionary representation of the operation.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls: Type['Operation'], data: Dict) -> 'Operation':
        """
        Deserialize the operation from a dictionary format.
        
        Args:
            data (Dict): A dictionary representation of the operation.
        
        Returns:
            Operation: An instance of the operation.
        """
        pass