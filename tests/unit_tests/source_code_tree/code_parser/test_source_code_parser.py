import pytest
import tempfile
import textwrap
from src.source_code_tree.code_entities.module_entity import ModuleEntity
from src.source_code_tree.code_parser.source_code_parser import SourceCodeParser

def test_parser_handles_file_with_function_and_class():
    # Arrange
    parser = SourceCodeParser()
    with tempfile.NamedTemporaryFile(suffix=".py") as temp:
        code_string = textwrap.dedent("""
        \"\"\"This is a test Python file\"\"\"
        
        def test_func():
            \"\"\"This is a test function\"\"\"
            pass
        
        class TestClass:
            \"\"\"This is a test class\"\"\"
            def test_method(self):
                \"\"\"This is a test method\"\"\"
                pass
        """)
        temp.write(code_string.encode('utf-8'))
        temp.seek(0)

        # Act
        result = parser.parse_source_code(temp.name)

        # Assert
        assert result.file_path == temp.name
        assert result.docstring == "This is a test Python file"
        assert len(result.functions) == 1
        assert "test_func" in result.functions
        assert result.functions["test_func"].docstring == "This is a test function"
        assert len(result.classes) == 1
        assert "TestClass" in result.classes
        assert result.classes["TestClass"].docstring == "This is a test class"
        assert len(result.classes["TestClass"].methods) == 1
        assert "test_method" in result.classes["TestClass"].methods
        assert result.classes["TestClass"].methods["test_method"].docstring == "This is a test method"


def test_parser_handles_standalone_function_with_multiple_arguments():
    parser = SourceCodeParser()
    with tempfile.NamedTemporaryFile(suffix=".py") as temp:
        code_string = textwrap.dedent("""
        def func_with_args(arg1: str, arg2: str):
            \"\"\"Function with multiple arguments\"\"\"
            pass
        """)
        temp.write(code_string.encode('utf-8'))
        temp.seek(0)

        result = parser.parse_source_code(temp.name)

        assert "func_with_args" in result.functions
        assert result.functions["func_with_args"].signature == "(arg1, arg2)"

def test_parser_handles_class_with_multiple_methods():
    parser = SourceCodeParser()
    with tempfile.NamedTemporaryFile(suffix=".py") as temp:
        code_string = textwrap.dedent("""
        class MyClass:
            \"\"\"Class with multiple methods\"\"\"
            
            def method_one(self):
                \"\"\"First method\"\"\"
                pass
            
            def method_two(self, arg):
                \"\"\"Second method with argument\"\"\"
                pass
        """)
        temp.write(code_string.encode('utf-8'))
        temp.seek(0)

        result: ModuleEntity = parser.parse_source_code(temp.name)

        assert "MyClass" in result.classes
        assert "method_one" in result.classes["MyClass"].methods
        assert "method_two" in result.classes["MyClass"].methods
        assert result.classes["MyClass"].methods["method_two"].signature == "(self, arg)"

# Other tests can follow a similar pattern
