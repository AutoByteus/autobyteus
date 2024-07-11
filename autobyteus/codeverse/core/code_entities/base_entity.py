"""
File: autobyteus/source_code_tree/code_entities/base_entity.py

This module contains classes that represent code entities. The main purpose of these classes is to
convert code entities into a human-readable description format.

Classes:
    - CodeEntity: An abstract base class that represents a generic code entity.
"""

from abc import ABC, abstractmethod

from autobyteus.codeverse.core.code_entities.code_entity_type import CodeEntityType



class CodeEntity(ABC):
    """
    Abstract base class representing a generic code entity.
    
    Code entities are parts or components in source code. 
    The class provides a structure for representing these entities
    and converting them into a human-readable description format.
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

    @property
    @abstractmethod
    def type(self) -> CodeEntityType:
        """
        Abstract property representing the type of code entity.
        Subclasses must implement this property.
        """
        pass

    @property
    def children(self):
        """
        Gets the children of this CodeEntity. By default, a CodeEntity has no children.

        Returns:
            list: Empty list, since a base CodeEntity has no children.
        """
        return []

    def to_description(self):
        """
        Convert the class entity to a string representation, keeping only the description part of the docstring.
                
        :return: A string representation of the class entity.
        :rtype: str
        """
        representation = f''
        
        # Add the docstring
        if self.docstring:
            # Split the docstring by lines
            docstring_lines = self.docstring.split('\n')
            # Initialize a list to hold description lines
            description_lines = []
            for line in docstring_lines:
                # When a line starts with a whitespace followed by ":", it's likely we're into parameter or return descriptions
                if line.strip().startswith(":"):
                    break
                description_lines.append(line)

            docstring_description = '\n'.join(description_lines)
            representation += f'{docstring_description.strip()}'
        
        return representation


    @abstractmethod
    def to_json(self) -> str:
        """
        Convert the code entity to json representation
        
        Note: This method should be implemented by the subclasses to
              provide specific conversion logic.
        
        :return: A json representation of the code entity.
        :rtype: str
        """

    @classmethod
    @abstractmethod
    def from_json(cls, representation: str) -> "CodeEntity":
        """
        Create a code entity from json representation.
        
        Note: This method should be implemented by the subclasses to
              provide specific creation logic.
        
        :param representation: The json representation of the code entity.
        :type representation: str
        :return: A code entity created from the representation.
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
