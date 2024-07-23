"""
This module contains the SourceCodeParser class which provides functionality to parse Python source code files.

The SourceCodeParser class has a method `parse_source_code` that takes a Python file's path as input, reads
the source code from the file, parses it, and extracts its module-level docstring, functions, classes,
and their associated docstrings. 

It returns a ModuleEntity object representing the module, containing FunctionEntity objects for each function 
and ClassEntity objects for each class, which in turn contain MethodEntity objects for each method within the class.
"""

import ast
from autobyteus.codeverse.core.code_entities.module_entity import ModuleEntity
from autobyteus.codeverse.core.code_parser.ast_node_visitor import AstNodeVisitor
from autobyteus.codeverse.core.file_explorer.file_reader import FileReader

class CodeFileParser:
    """
    This class provides functionality to parse Python source code.

    Methods:
        parse_source_code(filepath: str) -> ModuleEntity: Parses the source code from the file at filepath 
                                                          and extracts its docstring, functions, and classes.
    """

    def parse_source_code(self, filepath: str) -> ModuleEntity:
        """
        Reads and parses the source code from a .py file and extracts its docstring, functions and classes.

        Args:
            filepath (str): Path to a .py file.

        Returns:
            A ModuleEntity object containing the file's docstring, functions and classes,
            or None if the source_code could not be read or parsed.
        """
        source_code = FileReader.read_file(filepath)
        if source_code is None:
            return None

        module = ast.parse(source_code)
        visitor = AstNodeVisitor(filepath)

        module_entity = ModuleEntity(filepath, ast.get_docstring(module))

        functions = [visitor.visit(n) for n in module.body if isinstance(n, ast.FunctionDef)]
        classes = [visitor.visit(n) for n in module.body if isinstance(n, ast.ClassDef)]
        
        for function in functions:
            module_entity.add_function(function)

        for class_ in classes:
            module_entity.add_class(class_)

        return module_entity

