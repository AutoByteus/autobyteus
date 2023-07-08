"""
search_service.py

This module contains the SearchService class, which is responsible for searching for code entities.
The SearchService utilizes embeddings created from queries and retrieves relevant code entity embeddings
from the provided storage backend.

Classes:
    - SearchService: Manages the searching of code entities.
"""

from src.semantic_code.embedding.embedding_creator_factory import get_embedding_creator
from src.semantic_code.storage.storage_factory import get_storage
from src.singleton import SingletonMeta
from src.source_code_tree.code_entities.base_entity import CodeEntity


class SearchService(metaclass=SingletonMeta):
    """
    This class is responsible for searching for code entities by converting queries into embeddings and 
    retrieving relevant code entity embeddings from the provided storage backend.
    
    Attributes:
        base_storage (BaseStorage): Storage backend for retrieving code entity embeddings.
        embedding_creator (BaseEmbeddingCreator): Object responsible for creating embeddings from queries.
    """
    
    def __init__(self):
        """
        Initializes a SearchService with a storage backend retrieved by a get function and an embedding creator
        retrieved by get_embedding_creator function.
        """
        self.base_storage = get_storage()
        self.embedding_creator = get_embedding_creator()
    
    def search(self, query: str) -> list[CodeEntity]:
        """
        Searches for relevant code entities by converting the given query into an embedding and retrieving
        relevant embeddings from the storage backend.
        
        Args:
            query (str): The search query.
        
        Returns:
            list[CodeEntity]: A list of relevant code entities.
        """
        # Convert the query to an embedding
        query_embedding = self.embedding_creator.create_embedding(query)
        
        # Retrieve and return relevant code entities from the storage
        return self.base_storage.search(query_embedding)
