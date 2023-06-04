import pytest
import tempfile
import textwrap
from src.source_code_tree.code_parser.source_code_parser import SourceCodeParser

def test_parse_source_code_with_valid_python_file():
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

