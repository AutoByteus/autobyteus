# redis_result_converter.py

"""
Module providing a function to convert a Redis search result to a SearchResult object
containing entities

"""

from typing import Any
from redis.commands.search.result import Result
from src.semantic_code.search.search_result import ScoredEntity, SearchResult
from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.source_code_tree.code_entities.code_entity_factory import CodeEntityFactory

def convert_redis_result_to_search_result(redis_search_result: Result) -> SearchResult:
    """
    Converts a Redis search result to a SearchResult object.
    
    Args:
        redis_search_result (Result): The Redis search result to convert.
        
    Returns:
        SearchResult: The SearchResult object created from the Redis search result.
    """
    # Convert Redis documents to ScoredEntity objects
    entities = [ScoredEntity(CodeEntityFactory.create_entity(doc["type"], doc["representation"]), doc["vector_score"]) for doc in redis_search_result.docs]

    # Create SearchResult object
    search_result = SearchResult(total=redis_search_result.total, entities=entities)

    return search_result