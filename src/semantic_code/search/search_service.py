"""
search_service.py

This module contains the SearchService class, which is responsible for searching for code entities.
The SearchService utilizes embeddings created from queries and retrieves relevant code entity embeddings
from the provided storage backend.

Classes:
    - SearchService: Manages the searching of code entities.
"""

from src.semantic_code.embedding.base_embedding_creator import BaseEmbeddingCreator
from src.semantic_code.storage.base_storage import BaseStorage
from src.source_code_tree.code_entities.base_entity import CodeEntity


class SearchService:
    """
    This class is responsible for searching for code entities by converting queries into embeddings and 
    retrieving relevant code entity embeddings from the provided storage backend.
    
    Attributes:
        base_storage (BaseStorage): Storage backend for retrieving code entity embeddings.
        embedding_creator (BaseEmbeddingCreator): Object responsible for creating embeddings from queries.
    """
    
    def __init__(self, base_storage: BaseStorage, embedding_creator: BaseEmbeddingCreator):
        """
        Initializes a SearchService with the given storage service and embedding creator.
        
        Args:
            storage_service (BaseStorage): The storage backend for retrieving code entity embeddings.
            embedding_creator (BaseEmbeddingCreator): The object responsible for creating embeddings from queries.
        """
        self.base_storage = base_storage
        self.embedding_creator = embedding_creator
    
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
        return self.base_storage.retrieve(query_embedding)
