"""
File: src/source_code_tree/code_entities/base_entity.py

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
        file_path (str): The path of the source code file where the code entity is defined.
    
    Methods:
        __init__(self, docstring: str, file_path: str): Initializes a CodeEntity with the provided docstring and file path.
        to_representation(self): Abstract method to convert the code entity to a human-readable description format.
        to_unique_id(self): Abstract method to get a unique identifier for the code entity.
    """
    
    def __init__(self, docstring: str, file_path: str):
        """
        Initialize a generic code entity.
        
        :param docstring: Documentation string for the entity.
        :type docstring: str
        :param file_path: Path of the source code file where the code entity is defined.
        :type file_path: str
        """
        self.docstring = docstring
        self.file_path = file_path

    @abstractmethod
    def to_representation(self):
        """
        Convert the code entity to a human-readable description format.
        
        Note: This method should be implemented by the subclasses to
              provide specific conversion logic.
        
        :return: A human-readable description of the code entity.
        :rtype: str
        """

    @abstractmethod
    def to_unique_id(self):
        """
        Get a unique identifier for the code entity.
        
        Note: This method should be implemented by the subclasses to
              provide specific logic for generating a unique identifier.
              
        :return: A unique identifier for the code entity.
        :rtype: str
        """
