# tests/unit_tests/semantic_code/test_search_result.py

import json
import pytest

from src.semantic_code.search.search_result import ScoredEntity, SearchResult
from src.source_code_tree.code_entities.base_entity import CodeEntity

# Corrected Mock class for CodeEntity to test against
class MockCodeEntity(CodeEntity):
    def to_json(self) -> str:
        return json.dumps({"type": "mock"})
    
    def from_json(self, json_str: str):
        # Dummy implementation
        pass

    def to_unique_id(self):
        # Dummy implementation
        return "mock_unique_id"
    
    @property
    def type(self):
        # Dummy implementation
        return "mock_type"

@pytest.fixture
def mock_entity():
    # Providing mock values for 'docstring' and 'file_path'
    return MockCodeEntity(docstring="Mock docstring", file_path="mock/path")

@pytest.fixture
def mock_scored_entity(mock_entity):
    return ScoredEntity(entity=mock_entity, score=0.9)

def test_scored_entity_initialization_and_to_dict(mock_scored_entity, mock_entity):
    """ScoredEntity should correctly initialize and convert to dictionary."""
    assert mock_scored_entity.entity == mock_entity
    assert mock_scored_entity.score == 0.9
    assert mock_scored_entity.to_dict() == {"entity": {"type": "mock"}, "score": 0.9}

def test_search_result_initialization_and_to_json(mock_scored_entity):
    """SearchResult should correctly initialize and convert to json."""
    search_result = SearchResult(total=1, entities=[mock_scored_entity])
    assert search_result.total == 1
    assert search_result.entities == [mock_scored_entity]
    
    expected_json = json.dumps({"total": 1, "entities": [{"entity": {"type": "mock"}, "score": 0.9}]})
    assert search_result.to_json() == expected_json
