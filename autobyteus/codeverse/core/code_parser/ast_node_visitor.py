"""
File: autobyteus/source_code_tree/code_entities/ast_node_visitor.py

This module contains a class that extends the NodeVisitor class from Python's ast module.
It overrides methods to extract information from function and class definitions and returns
corresponding Entity objects.

Classes:
    - AstNodeVisitor: An extension of the NodeVisitor class that extracts information from
                      function and class definitions and returns corresponding Entity objects.
"""

import ast
from autobyteus.codeverse.core.code_entities.class_entity import ClassEntity
from autobyteus.codeverse.core.code_entities.function_entity import FunctionEntity
from autobyteus.codeverse.core.code_entities.method_entity import MethodEntity


class AstNodeVisitor(ast.NodeVisitor):
    """
    This class is an extension of the NodeVisitor class from Python's ast module.
    It overrides methods to extract information from function and class definitions and 
    returns corresponding Entity objects.

    Attributes:
        file_path (str): The path of the source code file being visited by the AstNodeVisitor.

    Methods:
        __init__(self, file_path: str): Initializes AstNodeVisitor with the provided file path.
        visit_FunctionDef(node): Returns a FunctionEntity object created from a function definition node.
        visit_ClassDef(node): Returns a ClassEntity object created from a class definition node.
    """

    def __init__(self, file_path: str):
        """
        Initialize AstNodeVisitor with the provided file path.

        :param file_path: The path of the source code file being visited.
        :type file_path: str
        """
        self.file_path = file_path

    def visit_FunctionDef(self, node):
        """
        Extracts the name, docstring, and signature of a function definition node and creates a FunctionEntity.

        Args:
            node (ast.FunctionDef): A node representing a function definition in the AST.

        Returns:
            A FunctionEntity object.
        """
        signature = self._get_signature(node)
        return FunctionEntity(node.name, ast.get_docstring(node), signature, self.file_path)

    def visit_ClassDef(self, node):
        """
        Extracts the name and docstring of a class definition node, creates a ClassEntity, and adds
        MethodEntity objects for each method in the class to the ClassEntity.

        Args:
            node (ast.ClassDef): A node representing a class definition in the AST.

        Returns:
            A ClassEntity object.
        """
        class_entity = ClassEntity(class_name=node.name, docstring=ast.get_docstring(node), file_path=self.file_path)
        methods = [self.visit(n) for n in node.body if isinstance(n, ast.FunctionDef)]

        for method in methods:
            method_entity = MethodEntity(method.name, method.docstring, method.signature, class_entity, self.file_path)
            class_entity.add_method(method_entity)

        return class_entity

    @staticmethod
    def _get_signature(function_node):
        """
        Helper method to get a function's signature from its AST node.

        Args:
            function_node (ast.FunctionDef): A function definition node in the AST.

        Returns:
            A string representing the function's signature.
        """
        args = [a.arg for a in function_node.args.args]
        return f'({", ".join(args)})'
