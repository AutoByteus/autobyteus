"""
File: src/source_code_tree/code_entities/method_entity.py

This module contains the MethodEntity class, which represents a method within a class in source code.
MethodEntity holds information such as the method's name, documentation string (docstring), signature,
and a reference to the class it belongs to.

Classes:
    - MethodEntity: Represents a method within a class in source code.
"""

from src.source_code_tree.code_entities.base_entity import CodeEntity


class MethodEntity(CodeEntity):
    """
    Represents a method in source code. It contains information such as the method's name,
    documentation string (docstring), signature, and the class entity it belongs to.
    
    Attributes:
        name (str): Name of the method.
        signature (str): Signature of the method.
        class_entity (CodeEntity): The CodeEntity instance representing the class to which this method belongs.
    
    Methods:
        __init__(self, name: str, docstring: str, signature: str, class_entity: CodeEntity, file_path: str):
            Initializes a MethodEntity instance.
        to_representation(self) -> str: Converts the MethodEntity to a human-readable string representation.
        to_unique_id(self) -> str: Returns a unique identifier for the MethodEntity.
    """

    def __init__(self, name: str, docstring: str, signature: str, class_entity: CodeEntity, file_path: str):
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

    def to_representation(self) -> str:
        """
        Converts the MethodEntity to a human-readable string representation.
        The output format is "Name: <name>, Signature: <signature>, Docstring: <docstring>, Class: <class_representation>"
        
        :return: A string representation of the method entity.
        :rtype: str
        """
        class_representation = self.class_entity.to_representation() if self.class_entity else "Unknown"
        return f"Name: {self.name}, Signature: {self.signature}, Docstring: {self.docstring}, Class: {class_representation}"
    
    def to_unique_id(self) -> str:
        """
        Returns a unique identifier for the MethodEntity. The unique identifier is a combination
        of the method's name and signature.
        
        :return: A unique identifier for the method entity.
        :rtype: str
        """
        return f"{self.name}:{self.signature}"
