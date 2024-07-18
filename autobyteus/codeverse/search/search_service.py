"""
search_service.py

This module contains the SearchService class, which is responsible for searching for code entities.
The SearchService utilizes embeddings created from queries and retrieves relevant code entity embeddings
from the provided storage backend.

Classes:
    - SearchService: Manages the searching of code entities.
"""

from autobyteus.codeverse.search.result_converter.redis_result_converter import convert_redis_result_to_search_result
from autobyteus.codeverse.search.search_result import SearchResult
from autobyteus.embeding.embedding_creator_factory import get_embedding_creator
from autobyteus.storage.embedding.storage.storage_factory import get_storage
from autobyteus.utils.singleton import SingletonMeta


class SearchService(metaclass=SingletonMeta):
    """
    This class is responsible for searching for code entities by converting queries into embeddings and 
    retrieving relevant code entity embeddings from the provided storage backend.
    """
    
    def __init__(self):
        """
        Initializes a SearchService with a storage backend retrieved by a get function and an embedding creator
        retrieved by get_embedding_creator function.
        """
        self.base_storage = get_storage()
        self.embedding_creator = get_embedding_creator()
    
    def search(self, query: str) -> SearchResult:
        """
        Searches for relevant code entities by converting the given query into an embedding and retrieving
        relevant embeddings from the storage backend.
        
        Args:
            query (str): The search query.
        
        Returns:
            SearchResult: The search result.
        """
        # Convert the query to an embedding
        query_embedding = self.embedding_creator.create_embedding(query)
        
        # Retrieve relevant documents from the storage
        redis_search_result = self.base_storage.search(query_embedding.tobytes())
        
        # Convert Redis search result to SearchResult
        search_result = convert_redis_result_to_search_result(redis_search_result)

        return search_result