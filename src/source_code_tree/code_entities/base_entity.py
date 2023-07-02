"""
File: src/source_code_tree/code_entities/base_entities.py

This module contains classes that represent code entities. The main purpose of these classes is to
convert code entities into a human-readable description format.

Classes:
    - CodeEntity: An abstract base class that represents a generic code entity.
"""

from abc import ABC, abstractmethod


class CodeEntity(ABC):
    """
    Abstract base class representing a generic code entity.
    
    Code entities are parts or components in source code. 
    The class provides a structure for representing these entities
    and converting them into a human-readable description format.
    
    Attributes:
        docstring (str): The documentation string for the code entity.
    
    Methods:
        __init__(self, docstring: str): Initializes a CodeEntity with the provided docstring.
        to_representation(self): Abstract method to convert the code entity to a human-readable description format.
    """
    
    def __init__(self, docstring: str):
        """
        Initialize a generic code entity.
        
        :param docstring: Documentation string for the entity.
        :type docstring: str
        """
        self.docstring = docstring

    @abstractmethod
    def to_representation(self):
        """
        Convert the code entity to a human-readable description format.
        
        Note: This method should be implemented by the subclasses to
              provide specific conversion logic.
        
        :return: A human-readable description of the code entity.
        :rtype: str
        """
