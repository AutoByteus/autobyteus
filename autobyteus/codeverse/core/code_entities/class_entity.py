"""
File: autobyteus/source_code_tree/code_entities/class_entity.py

This module defines the ClassEntity class which represents a class in code that can be converted to string representations.

Classes:
    - ClassEntity: Represents a class in code that can be converted to string representations.
"""
import json

from autobyteus.codeverse.core.code_entities.base_entity import CodeEntity
from autobyteus.codeverse.core.code_entities.code_entity_type import CodeEntityType


class ClassEntity(CodeEntity):
    """
    Represents a class in code that can be converted to string representations.
    """
    
    def __init__(self, docstring: str, class_name: str, file_path: str, methods: dict = None):
        """
        Initialize a class entity.
        
        :param docstring: Documentation string for the class.
        :type docstring: str
        :param class_name: Name of the class.
        :type class_name: str
        :param file_path: Path of the source code file where the class entity is defined.
        :type file_path: str
        :param methods: Dictionary holding information on methods defined within the class, defaults to None.
        :type methods: dict, optional
        """
        super().__init__(docstring, file_path)
        self.class_name = class_name
        self.methods = methods or {}

    @property
    def type(self) -> CodeEntityType:
        """
        Property representing the type of class entity.
        """
        return CodeEntityType.CLASS
    
    @property
    def children(self):
        """
        Gets the children of this ClassEntity, which are the methods defined in the class.

        Returns:
            list: List of FunctionEntity instances representing the methods in this class.
        """
        return list(self.methods.values())

    def add_method(self, method_entity):
        """
        Add a method entity to the class.
        
        :param method_entity: The method entity to add. It is expected to have a 'name' attribute representing the method name.
        :type method_entity: object
        """
        self.methods[method_entity.name] = method_entity


    def to_json(self) -> str:
        """
        Convert the class entity to json representation
        
        :return: A json representation of the class entity.
        :rtype: str
        """
        return json.dumps({
            'class_name': self.class_name,
            'docstring': self.docstring,
            'file_path': self.file_path
        })

    @classmethod
    def from_json(cls, representation: str) -> "ClassEntity":
        """
        Create a class entity from json representation.
        
        :param representation: The json representation of the class entity.
        :type representation: str
        :return: A class entity created from the representation.
        """
        data = json.loads(representation)
        return cls(
            class_name=data['class_name'], 
            docstring=data['docstring'], 
            file_path=data['file_path']
        )

    def to_unique_id(self):
        """
        Get a unique identifier for the class entity.
        
        Note: The unique identifier is a combination of the file path and class name.
              
        :return: A unique identifier for the class entity.
        :rtype: str
        """
        return f"{self.file_path}:{self.class_name}"
    

    def __eq__(self, other):
        if isinstance(other, ClassEntity):
            return (self.name == other.class_name and
                    self.docstring == other.docstring and
                    self.file_path == other.file_path)
        return False