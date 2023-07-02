"""
This module defines the ClassEntity class which represents a class in code that can be converted to string representations.

Classes:
    - ClassEntity: Represents a class in code that can be converted to string representations.
"""

from src.source_code_tree.code_entities import CodeEntity


class ClassEntity(CodeEntity):
    """
    Represents a class in code that can be converted to string representations.
    
    Attributes:
        docstring (str): The documentation string for the class.
        class_name (str): The name of the class.
        methods (dict): A dictionary holding information on methods defined within the class, with method names as keys and method entities as values.
    
    Methods:
        __init__(self, docstring: str, class_name: str, methods: dict = None): Initializes a ClassEntity with the provided docstring, class name, and methods.
        add_method(self, method_entity): Add a method entity to the class.
        to_representation(self): Convert the class entity to a string representation.
    """
    
    def __init__(self, docstring: str, class_name: str, methods: dict = None):
        """
        Initialize a class entity.
        
        :param docstring: Documentation string for the class.
        :type docstring: str
        :param class_name: Name of the class.
        :type class_name: str
        :param methods: Dictionary holding information on methods defined within the class, defaults to None.
        :type methods: dict, optional
        """
        super().__init__(docstring)
        self.class_name = class_name
        self.methods = methods or {}

    def add_method(self, method_entity):
        """
        Add a method entity to the class.
        
        :param method_entity: The method entity to add. It is expected to have a 'name' attribute representing the method name.
        :type method_entity: object
        """
        self.methods[method_entity.name] = method_entity

    def to_representation(self):
        """
        Convert the class entity to a string representation.
                
        :return: A string representation of the class entity.
        :rtype: str
        """
        # Start with the class name
        representation = f'class {self.class_name}:\n'
        
        # Add the docstring
        if self.docstring:
            representation += f'    """{self.docstring}"""\n'
        
        return representation
