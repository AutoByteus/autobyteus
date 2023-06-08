import ast
from src.semantic_code.index.document.entities import FunctionEntity, ClassEntity, MethodEntity

class AstNodeVisitor(ast.NodeVisitor):
    """
    This class is an extension of the NodeVisitor class from Python's ast module.
    It overrides methods to extract information from function and class definitions and 
    returns corresponding Entity objects.

    Methods:
        visit_FunctionDef(node): Returns a FunctionEntity object created from a function definition node.
        visit_ClassDef(node): Returns a ClassEntity object created from a class definition node.
    """

    def visit_FunctionDef(self, node):
        """
        Extracts the name, docstring, and signature of a function definition node and creates a FunctionEntity.

        Args:
            node (ast.FunctionDef): A node representing a function definition in the AST.

        Returns:
            A FunctionEntity object.
        """
        signature = self._get_signature(node)
        return FunctionEntity(node.name, ast.get_docstring(node), signature)

    def visit_ClassDef(self, node):
        """
        Extracts the name and docstring of a class definition node, creates a ClassEntity, and adds
        MethodEntity objects for each method in the class to the ClassEntity.

        Args:
            node (ast.ClassDef): A node representing a class definition in the AST.

        Returns:
            A ClassEntity object.
        """
    def visit_ClassDef(self, node):
        class_entity = ClassEntity(class_name=node.name, docstring=ast.get_docstring(node))
        methods = [self.visit(n) for n in node.body if isinstance(n, ast.FunctionDef)]

        for method in methods:
            method_entity = MethodEntity(method.name, method.docstring, method.signature)
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
