"""
index_service.py

This module contains the IndexService class, which is responsible for indexing code entities.
The IndexService utilizes embeddings created from code entities and stores them using a storage backend
created by a factory method.

Classes:
    - IndexService: Manages the indexing of code entities.
"""

from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.semantic_code.embedding.embedding_creator_factory import EmbeddingCreatorFactory
from src.semantic_code.storage.storage_factory import create_storage


class IndexService:
    """
    This class is responsible for indexing code entities by creating embeddings for them and storing them using
    a storage backend created by a factory method.

    Attributes:
        base_storage (BaseStorage): Storage backend for storing code entity embeddings.
        embedding_creator (BaseEmbeddingCreator): Object responsible for creating embeddings for code entities.
    """
    
    def __init__(self):
        """
        Initializes an IndexService with a storage backend created by a factory method and an embedding creator
        created by the EmbeddingCreatorFactory.
        """
        try:
            self.base_storage = create_storage()
            self.embedding_creator = EmbeddingCreatorFactory.create_embedding_creator()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize IndexService: {str(e)}")
    
    def index(self, code_entity: CodeEntity):
        """
        Indexes a code entity by creating an embedding for it and storing it using the provided storage backend.

        Args:
            code_entity (CodeEntity): The code entity to be indexed.

        Note:
            The provided code_entity should have a method called `to_representation` which should return an
            appropriate representation of the code entity that can be passed to the embedding creator.
        """
        try:
            embedding = self.embedding_creator.create_embedding(code_entity.to_representation())
            self.base_storage.store(code_entity.to_representation(), embedding)
        except Exception as e:
            raise RuntimeError(f"Failed to index code entity: {str(e)}")
