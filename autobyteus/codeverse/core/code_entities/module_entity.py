"""
File: autobyteus/source_code_tree/code_entities/module_entity.py

This module defines the ModuleEntity class which represents a module in source code.
It is used to store and represent information about a module such as its file path, docstring,
classes, and functions. The ModuleEntity is a subclass of CodeEntity.

Classes:
    - ModuleEntity: Represents a module in source code.
"""

import json
from autobyteus.source_code_tree.code_entities.base_entity import CodeEntity
from autobyteus.source_code_tree.code_entities.code_entity_type import CodeEntityType


class ModuleEntity(CodeEntity):
    def __init__(self, file_path: str, docstring: str, classes: dict = None, functions: dict = None):
        """
        Initialize a ModuleEntity instance with the given file path, docstring, classes, and functions.
        
        :param file_path: Path to the file where the module is defined. (str)
        :param docstring: Documentation string for the module. (str)
        :param classes: Dictionary holding information on classes defined within the module. Defaults to None. (dict)
        :param functions: Dictionary holding information on functions defined within the module. Defaults to None. (dict)
        """
        super().__init__(docstring, file_path)
        self.classes = classes or {}
        self.functions = functions or {}

    @property
    def type(self) -> CodeEntityType:
        """
        Property representing the type of module entity.
        """
        return CodeEntityType.MODULE
    
    @property
    def children(self):
        """
        Gets the children of this ModuleEntity, which are the classes and functions defined in the module.

        Returns:
            list: List of ClassEntity and FunctionEntity instances representing the classes and functions in this module.
        """
        return list(self.classes.values()) + list(self.functions.values())
    

    def add_class(self, class_entity):
        """
        Add a class entity to the module.
        
        :param class_entity: The class entity to add. (ClassEntity)
        """
        self.classes[class_entity.class_name] = class_entity

    def add_function(self, function_entity):
        """
        Add a function entity to the module.
        
        :param function_entity: The function entity to add. (FunctionEntity)
        """
        self.functions[function_entity.name] = function_entity

    def to_unique_id(self):
        """
        Get a unique identifier for the module entity.
        
        Note: This method is implemented to provide specific logic for generating a unique identifier.
              
        :return: A unique identifier for the module entity.
        :rtype: str
        """
        return f"Module:{hash(self.file_path)}"

    def to_json(self) -> str:
        """
        Convert the module entity to json representation
        
        :return: A json representation of the module entity.
        :rtype: str
        """
        return json.dumps({
            'docstring': self.docstring,
            'file_path': self.file_path,
            'type': 'module'
        })

    @classmethod
    def from_json(cls, representation: str, classes: dict = None, functions: dict = None) -> "ModuleEntity":
        """
        Create a module entity from json representation.
        
        :param representation: The json representation of the module entity.
        :type representation: str
        :param classes: Dictionary holding information on classes defined within the module, defaults to None. (dict)
        :param functions: Dictionary holding information on functions defined within the module, defaults to None. (dict)
        :return: A module entity created from the representation.
        """
        data = json.loads(representation)
        return cls(
            file_path=data['file_path'], 
            docstring=data['docstring'], 
            classes=classes, 
            functions=functions
        )
    
    def __eq__(self, other):
        if isinstance(other, ModuleEntity):
            return (self.docstring == other.docstring and
                    self.file_path == other.file_path)
        return False