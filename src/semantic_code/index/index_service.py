"""
index_service.py

This module contains the IndexService class, which is responsible for indexing code entities.
The IndexService utilizes embeddings created from code entities and stores them using a storage backend
retrieved by a get function.

Classes:
    - IndexService: Manages the indexing of code entities.
"""

from src.semantic_code.storage.base_storage import BaseStorage
from src.singleton import SingletonMeta
from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.semantic_code.embedding.embedding_creator_factory import get_embedding_creator
from src.semantic_code.storage.storage_factory import get_storage


class IndexService(metaclass=SingletonMeta):
    """
    This class is responsible for indexing code entities by creating embeddings for them and storing them using
    a storage backend retrieved by a get function.

    Attributes:
        base_storage (BaseStorage): Storage backend for storing code entity embeddings.
        embedding_creator (BaseEmbeddingCreator): Object responsible for creating embeddings for code entities.
    """
    
    def __init__(self):
        """
        Initializes an IndexService with a storage backend retrieved by a get function and an embedding creator
        retrieved by get_embedding_creator function.
        """
        try:
            self.base_storage: BaseStorage = get_storage()
            self.embedding_creator = get_embedding_creator()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize IndexService: {str(e)}")
    
    def index(self, code_entity: CodeEntity):
        """
        Indexes a code entity by creating an embedding for it and storing it using the provided storage backend.

        Args:
            code_entity (CodeEntity): The code entity to be indexed.
        """
        try:
            embedding = self.embedding_creator.create_embedding(code_entity.to_representation())
            self.base_storage.store(code_entity.to_unique_id(), code_entity, embedding.tobytes())
        except Exception as e:
            raise RuntimeError(f"Failed to index code entity: {str(e)}")
