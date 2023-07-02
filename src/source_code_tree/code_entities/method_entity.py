"""
File: src/source_code_tree/code_entities/method_entity.py

This module contains the MethodEntity class, which represents a method within a class in source code.
MethodEntity holds information such as the method's name, documentation string (docstring), signature,
and a reference to the class it belongs to.

Classes:
    - MethodEntity: Represents a method within a class in source code.
"""

from src.source_code_tree.code_entities import CodeEntity
from src.source_code_tree.code_entities.class_entity import ClassEntity


class MethodEntity(CodeEntity):
    """
    Represents a method in source code. It contains information such as the method's name,
    documentation string (docstring), signature, and the class entity it belongs to.
    
    :param name: Name of the method.
    :param docstring: Documentation string for the method.
    :param signature: Signature of the method.
    :param class_entity: The ClassEntity instance representing the class to which this method belongs.
    
    :ivar name: Stores the name of the method.
    :ivar docstring: Stores the docstring of the method.
    :ivar signature: Stores the signature of the method.
    :ivar class_entity: Stores the ClassEntity instance to which this method belongs.
    """

    def __init__(self, name: str, docstring: str, signature: str, class_entity: ClassEntity):
        """
        Initialize a MethodEntity instance with the given name, docstring, signature, and class entity.
        
        :param name: Name of the method. This should be a string.
        :type name: str
        :param docstring: Documentation string for the method. This should be a string.
        :type docstring: str
        :param signature: Signature of the method. This should be a string representing the method's signature.
        :type signature: str
        :param class_entity: The ClassEntity instance representing the class to which this method belongs.
        :type class_entity: ClassEntity
        """
        super().__init__(docstring)
        self.name = name
        self.signature = signature
        self.class_entity = class_entity

    def to_representation(self) -> str:
        """
        Converts the MethodEntity to a human-readable string representation.
        The output format is "Name: <name>, Signature: <signature>, Docstring: <docstring>, Class: <class_name>"
        
        :return: A string representation of the method entity.
        :rtype: str
        """
        class_name = self.class_entity.class_name if self.class_entity else "Unknown"
        return f"Name: {self.name}, Signature: {self.signature}, Docstring: {self.docstring}, Class: {class_name}"
