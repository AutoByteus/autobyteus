# File Path: tests/integration_tests/semantic_code/search/test_search_service_integration.py

"""
tests/integration_tests/semantic_code/search/test_search_service_integration.py

Integration tests for the SearchService class to ensure that it correctly searches for code entities.
"""

import pytest
from src.semantic_code.search.search_service import SearchService
from src.source_code_tree.code_entities.function_entity import FunctionEntity
from src.semantic_code.index.index_service import IndexService


@pytest.fixture
def valid_function_entity() -> FunctionEntity:
    """
    This fixture creates and returns a valid instance of FunctionEntity with a name, docstring, signature, and file_path.
    """
    return FunctionEntity(name="test_function", docstring="This is a test function.", signature="def test_function(arg1, arg2):", file_path="src/my_module/my_file.py")


@pytest.mark.integration
def test_should_search_code_entity_with_real_storage(valid_function_entity: FunctionEntity):
    """
    This test checks if the SearchService correctly retrieves a previously indexed code entity with a real storage backend.
    Note: This assumes that a real storage backend is configured and accessible.
    """
    # First, we index a valid code entity with the IndexService
    index_service = IndexService()
    try:
        index_service.index(valid_function_entity)
    except Exception as e:
        pytest.fail(f"Indexing failed with exception: {str(e)}")

    # Then, we use the SearchService to search for the previously indexed entity
    search_service = SearchService()
    try:
        result = search_service.search(valid_function_entity.to_description())

        # Assert that the returned result includes the previously indexed entity
        assert valid_function_entity in [scored_entity.entity for scored_entity in result.entities]
    except Exception as e:
        pytest.fail(f"Search failed with exception: {str(e)}")