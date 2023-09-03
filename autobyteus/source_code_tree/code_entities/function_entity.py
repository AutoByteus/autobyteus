# File Path: autobyteus/source_code_tree/code_entities/function_entity.py
"""
File: autobyteus/source_code_tree/code_entities/function_entity.py

This module defines the FunctionEntity class, which represents a function within a codebase.
The FunctionEntity holds information about the function such as its name, documentation string,
and signature. It inherits from the CodeEntity class and provides an implementation for the
`to_description` method which converts the function entity to a human-readable description format.

Classes:
    - FunctionEntity: Represents a function in a codebase.
"""
import json
from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.source_code_tree.code_entities.code_entity_type import CodeEntityType


class FunctionEntity(CodeEntity):
    """
    Represents a function in a codebase.
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

    @property
    def type(self) -> CodeEntityType:
        """
        Property representing the type of function entity.
        """
        return CodeEntityType.FUNCTION
    
    def to_unique_id(self):
        """
        Get a unique identifier for the function entity.
        
        A unique identifier is created by combining the file path and the function's name.
        
        :return: A unique identifier for the function entity.
        :rtype: str
        """
        return f"{self.file_path}::{self.name}"


    def to_json(self) -> str:
        """
        Convert the function entity to json representation
        
        :return: A json representation of the function entity.
        :rtype: str
        """
        return json.dumps({
            'name': self.name,
            'docstring': self.docstring,
            'file_path': self.file_path,
            'signature': self.signature,
            'type': 'function'
        })

    @classmethod
    def from_json(cls, representation: str) -> "FunctionEntity":
        """
        Create a function entity from json representation.
        
        :param representation: The json representation of the function entity.
        :type representation: str
        :return: A function entity created from the representation.
        """
        data = json.loads(representation)
        return cls(
            name=data['name'], 
            docstring=data['docstring'], 
            signature=data['signature'],
            file_path=data['file_path'], 
        )
    
    def __eq__(self, other):
        if isinstance(other, FunctionEntity):
            return (self.name == other.name and
                    self.docstring == other.docstring and
                    self.signature == other.signature and
                    self.file_path == other.file_path)
        return False