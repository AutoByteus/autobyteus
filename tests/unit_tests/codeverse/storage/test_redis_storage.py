# File: tests/unit/src/semantic_code/storage/test_redis_storage.py
import pytest
from unittest.mock import MagicMock
from autobyteus.codeverse.core.code_entities.base_entity import CodeEntity
from autobyteus.storage.embedding.storage.redis_storage import RedisStorage

@pytest.fixture
def mock_redis_client():
    # Mock the redis client to avoid actual connection to a Redis server during testing.
    return MagicMock()


@pytest.fixture
def redis_storage(mock_redis_client):
    # Initialize the RedisStorage class with a mock redis client.
    storage = RedisStorage()
    storage.redis_client = mock_redis_client
    return storage


class MockCodeEntity(CodeEntity):
    def to_description(self):
        return "Mock Code Entity"


def test_store_stores_code_entity_and_embedding_in_redis(redis_storage, mock_redis_client):
    mock_entity = MockCodeEntity(docstring="This is a docstring.")
    mock_vector = [1.0, 2.0]
    
    # Call store method
    redis_storage.store(key="entity:1", entity=mock_entity, vector=mock_vector)

    # Check if the redis client hset method was called with the correct parameters
    expected_post_hash = {
        "id": "entity:1",
        "docstring": mock_entity.docstring,
        "embedding": mock_vector
    }
    mock_redis_client.hset.assert_called_once_with(name="code_entity:entity:1", mapping=expected_post_hash)


def test_retrieve_retrieves_code_entity_from_redis(redis_storage, mock_redis_client):
    # Define what the mock redis_client should return for hgetall
    mock_redis_client.hgetall.return_value = {"id": "entity:1", "docstring": "This is a docstring.", "embedding": [1.0, 2.0]}
    
    # Call retrieve method
    result = redis_storage.retrieve(key="entity:1")

    # Assert the expected result
    assert result == {"id": "entity:1", "docstring": "This is a docstring.", "embedding": [1.0, 2.0]}


def test_search_returns_closest_code_entities(redis_storage, mock_redis_client):
    # Mock search result
    mock_search_result = [('entity:1', ['1.0']), ('entity:2', ['2.0'])]
    mock_redis_client.ft.return_value.search.return_value = mock_search_result

    # Call search method
    result = redis_storage.search(vector=[1.0, 2.0], top_k=2)

    # Assert the expected result
    assert result == mock_search_result
