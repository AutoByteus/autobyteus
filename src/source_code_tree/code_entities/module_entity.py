"""
File: src/source_code_tree/code_entities/module_entity.py

This module defines the ModuleEntity class which represents a module in source code.
It is used to store and represent information about a module such as its file path, docstring,
classes, and functions. The ModuleEntity is a subclass of CodeEntity and provides an
implementation for the `to_representation` method as per the contract defined in the base class.

Classes:
    - ModuleEntity: Represents a module in source code.
"""

from src.source_code_tree.code_entities.base_entity import CodeEntity


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

    def to_representation(self):
        """
        Convert the module entity to a human-readable description format. This method returns a string
        representing the module, including its file path, docstring, classes, and functions.
        
        :return: A human-readable description of the module entity. (str)
        """
        description = [f"Module: {self.file_path}"]

        if self.docstring:
            description.append(f"Docstring: {self.docstring}")

        return "\n".join(description)

    def to_unique_id(self):
        """
        Get a unique identifier for the module entity.
        
        Note: This method is implemented to provide specific logic for generating a unique identifier.
              
        :return: A unique identifier for the module entity.
        :rtype: str
        """
        return f"Module:{hash(self.file_path)}"
