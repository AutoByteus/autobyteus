"""
Module: base_storage.py
Description: Defines the abstract base class for storage implementations.
"""

from abc import ABC, abstractmethod

from src.singleton import ABCSingletonMeta
from src.source_code_tree.code_entities.base_entity import CodeEntity

class BaseStorage(metaclass=ABCSingletonMeta):
    """
    BaseStorage is an abstract base class that defines the interface for storage implementations.
    Subclasses must implement the store and retrieve methods.

    Methods:
        store(key: str, entity: CodeEntity, embedding): Stores the embedding with the given key.
        retrieve(query: str): Retrieves the embedding for the given query.
    """

    @abstractmethod
    def store(self, key: str, entity: CodeEntity, embedding):
        """
        Stores the embedding with the given key.

        Args:
            key (str): The key used to store the embedding.
            entity (CodeEntity): The code entity to be stored.
            embedding: The embedding to be stored.
        """
        pass


    @abstractmethod
    def retrieve(self, query: str):
        """
        Retrieves the embedding for the given query.

        Args:
            query (str): The query used to retrieve the embedding.

        Returns:
            The embedding associated with the query.
        """
        pass

    @abstractmethod
    def search(self, embedding, top_k=5):
        """
        Searches for the top_k closest embeddings to the given vector.

        Args:
            embedding: The query embedding vector.
            top_k (int): The number of closest embeddings to retrieve. Defaults to 5.

        Returns:
            A list of closest embeddings.
        """
        pass