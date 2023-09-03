"""
File: autobyteus/source_code_tree/code_entities/method_entity.py

This module contains the MethodEntity class, which represents a method within a class in source code.
MethodEntity holds information such as the method's name, documentation string (docstring), signature,
and a reference to the class it belongs to.

Classes:
    - MethodEntity: Represents a method within a class in source code.
"""
import json
from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.source_code_tree.code_entities.code_entity_type import CodeEntityType


class MethodEntity(CodeEntity):
    """
    Represents a method in source code. It contains information such as the method's name,
    documentation string (docstring), signature, and the class entity it belongs to.
    """

    def __init__(self, name: str, docstring: str, signature: str, file_path: str, class_entity: CodeEntity = None):
        """
        Initialize a MethodEntity instance with the given name, docstring, signature, and class entity.
        
        :param name: Name of the method.
        :type name: str
        :param docstring: Documentation string for the method.
        :type docstring: str
        :param signature: Signature of the method.
        :type signature: str
        :param class_entity: The CodeEntity instance representing the class to which this method belongs.
        :type class_entity: CodeEntity
        :param file_path: Path of the source code file where the code entity is defined.
        :type file_path: str
        """
        super().__init__(docstring, file_path)
        self.name = name
        self.signature = signature
        self.class_entity = class_entity


    @property
    def type(self) -> CodeEntityType:
        """
        Property representing the type of method entity.
        """
        return CodeEntityType.METHOD
    
    def to_unique_id(self) -> str:
        """
        Returns a unique identifier for the MethodEntity. The unique identifier is a combination
        of the method's name and signature.
        
        :return: A unique identifier for the method entity.
        :rtype: str
        """
        return f"{self.name}:{self.signature}"

    def to_json(self) -> str:
        """
        Convert the method entity to json representation
        
        :return: A json representation of the method entity.
        :rtype: str
        """
        return json.dumps({
            'name': self.name,
            'docstring': self.docstring,
            'file_path': self.file_path,
            'type': 'method'
        })

    @classmethod
    def from_json(cls, representation: str) -> "MethodEntity":
        """
        Create a method entity from json representation.
        
        :param representation: The json representation of the method entity.
        :type representation: str
        :return: A method entity created from the representation.
        """
        data = json.loads(representation)
        return cls(
            name=data['name'], 
            docstring=data['docstring'], 
            signature=data['signature'],
            file_path=data['file_path'], 
        )

    def __eq__(self, other):
        if isinstance(other, MethodEntity):
            return (self.name == other.name and
                    self.docstring == other.docstring and
                    self.signature == other.signature and
                    self.file_path == other.file_path)
        return False