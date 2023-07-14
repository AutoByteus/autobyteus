# File Path: tests/integration_tests/semantic_code/index/test_index_service_integration.py
"""
tests/integration_tests/semantic_code/index/test_index_service_integration.py

Integration tests for the IndexService class to ensure that it correctly indexes code entities.
"""

import tempfile
import pytest
from src.semantic_code.index.index_service import IndexService
from src.source_code_tree.code_entities.function_entity import FunctionEntity
from src.source_code_tree.code_parser.source_code_parser import SourceCodeParser

@pytest.fixture
def valid_function_entity():
    """
    This fixture creates and returns a valid instance of FunctionEntity with a name, docstring, signature, and file_path.
    """
    # Creating a real instance of FunctionEntity with name, docstring, signature, and file_path
    return FunctionEntity(name="test_function", docstring="This is a test function.", signature="def test_function(arg1, arg2):", file_path="src/my_module/my_file.py")


@pytest.mark.integration
def test_should_index_code_entity_with_real_storage(valid_function_entity, setup_and_teardown_redis):
    """
    This test checks if the IndexService correctly indexes a valid code entity with a real storage backend.
    Note: This assumes that a real storage backend is configured and accessible.
    """
    # Test IndexService should correctly index a valid code entity with a real storage backend
    index_service = IndexService()
    try:
        index_service.index(valid_function_entity)
    finally:
        # Clean up the test data after each test
        index_service.base_storage.flush_db()  # Assuming IndexService has access to redis_client


@pytest.fixture
def temp_source_code_file():
    source_code = """
    def test_function(arg1, arg2):
        \"\"\"This is a test function\"\"\"
        pass

    class TestClass:
        \"\"\"This is a test class\"\"\"
        def test_method(self):
            \"\"\"This is a test method\"\"\"
            pass
    """
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp:
        temp.write(source_code.encode('utf-8'))
        temp.seek(0)
        yield temp.name  # This will be the input for the tests

@pytest.mark.integration
def test_end_to_end_indexing_and_searching(temp_source_code_file, setup_and_teardown_redis):
    """
    This test checks if the IndexService correctly indexes a module entity and 
    that the module entity can be correctly found afterwards.
    Note: This assumes that a real storage backend is configured and accessible.
    """
    # Arrange
    file_path = temp_source_code_file
    index_service = IndexService()
    parser = SourceCodeParser()

    # Act
    parsed_module = parser.parse_source_code(file_path)
    index_service.index(parsed_module)

    # Cleanup: Ensure that the database is flushed after each test
    try:
        indexed_module = index_service.search("test function")
    finally:
        index_service.base_storage.flush_db()

    # Assert
    assert indexed_module.file_path == parsed_module.file_path
    assert indexed_module.docstring == parsed_module.docstring
    assert len(indexed_module.functions) == len(parsed_module.functions)
    assert len(indexed_module.classes) == len(parsed_module.classes)
    for function in parsed_module.functions.values():
        assert function in indexed_module.functions.values()
    for class_entity in parsed_module.classes.values():
        assert class_entity in indexed_module.classes.values()
