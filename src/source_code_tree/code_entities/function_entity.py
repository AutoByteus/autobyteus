# File Path: src/source_code_tree/code_entities/function_entity.py
"""
File: src/source_code_tree/code_entities/function_entity.py

This module defines the FunctionEntity class, which represents a function within a codebase.
The FunctionEntity holds information about the function such as its name, documentation string,
and signature. It inherits from the CodeEntity class and provides an implementation for the
`to_representation` method which converts the function entity to a human-readable description format.

Classes:
    - FunctionEntity: Represents a function in a codebase.
"""

from src.source_code_tree.code_entities.base_entity import CodeEntity


class FunctionEntity(CodeEntity):
    """
    Represents a function in a codebase.
    
    Attributes:
        name (str): The name of the function.
        signature (str): The signature of the function.
    
    Methods:
        __init__(self, name: str, docstring: str, signature: str, file_path: str): Initializes a FunctionEntity with the provided name, docstring, signature, and file_path.
        to_representation(self): Convert the function entity to a string representation.
        to_unique_id(self): Get a unique identifier for the function entity.
    """
    
    def __init__(self, name: str, docstring: str, signature: str, file_path: str):
        """
        Initialize a function entity.
        
        :param name: Name of the function.
        :type name: str
        
        :param docstring: Documentation string for the function.
        :type docstring: str
        
        :param signature: Signature of the function.
        :type signature: str
        
        :param file_path: Path of the source code file where the function is defined.
        :type file_path: str
        """
        super().__init__(docstring, file_path)
        self.name = name
        self.signature = signature

    def to_representation(self):
        """
        Convert the FunctionEntity to a human-readable description format.
        
        This method creates a string representation by combining the function's
        name, signature, and documentation string.
        
        :return: A human-readable description of the function entity.
        :rtype: str
        """
        # Create a human-readable description
        description = f"Function: {self.name}\n"
        description += f"Signature: {self.signature}\n"
        description += f"Documentation: {self.docstring}\n"
        
        # Return the human-readable description
        return description
    
    def to_unique_id(self):
        """
        Get a unique identifier for the function entity.
        
        A unique identifier is created by combining the file path and the function's name.
        
        :return: A unique identifier for the function entity.
        :rtype: str
        """
        return f"{self.file_path}::{self.name}"
