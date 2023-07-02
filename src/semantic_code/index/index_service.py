"""
index_service.py

This module contains the IndexService class, which is responsible for indexing code entities.
The IndexService utilizes embeddings created from code entities and stores them using the provided storage backend.

Classes:
    - IndexService: Manages the indexing of code entities.
"""

from src.semantic_code.embedding.base_embedding_creator import BaseEmbeddingCreator
from src.semantic_code.storage.base_storage import BaseStorage
from src.source_code_tree.code_entities.base_entity import CodeEntity


class IndexService:
    """
    This class is responsible for indexing code entities by creating embeddings for them and storing them using
    a provided storage backend.
    
    Attributes:
        base_storage (BaseStorage): Storage backend for storing code entity embeddings.
        embedding_creator (BaseEmbeddingCreator): Object responsible for creating embeddings for code entities.
    """
    
    def __init__(self, base_storage: BaseStorage, embedding_creator: BaseEmbeddingCreator):
        """
        Initializes an IndexService with the given storage backend and embedding creator.
        
        Args:
            base_storage (BaseStorage): The storage backend for storing code entity embeddings.
            embedding_creator (BaseEmbeddingCreator): The object responsible for creating embeddings for code entities.
        """
        self.base_storage = base_storage
        self.embedding_creator = embedding_creator
    
    def index(self, code_entity: CodeEntity):
        """
        Indexes a code entity by creating an embedding for it and storing it using the provided storage backend.
        
        Args:
            code_entity (CodeEntity): The code entity to be indexed.
            
        Note:
            The provided code_entity should have a method called `to_representation` which should return an
            appropriate representation of the code entity that can be passed to the embedding creator.
        """
        embedding = self.embedding_creator.create_embedding(code_entity.to_representation())
        self.base_storage.store(code_entity.to_representation(), embedding)
