"""
tests/integration_tests/semantic_code/index/test_index_service_integration.py

Integration tests for the IndexService class to ensure that it correctly indexes code entities.
"""

import pytest
from src.semantic_code.index.index_service import IndexService
from src.source_code_tree.code_entities.function_entity import FunctionEntity
from src.semantic_code.storage.storage_factory import create_storage


@pytest.fixture
def valid_function_entity():
    # Creating a real instance of FunctionEntity with name, docstring, and signature
    return FunctionEntity(name="test_function", docstring="This is a test function.", signature="def test_function():")


@pytest.mark.integration
def test_should_index_code_entity_with_real_storage(valid_function_entity):
    # Test IndexService should correctly index a valid code entity with a real storage backend
    # Note: This assumes that a real storage backend is configured and accessible
    
    index_service = IndexService(create_storage())
    try:
        index_service.index(valid_function_entity)
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


# You can add more tests to check retrieval of the indexed entity, error handling etc.
