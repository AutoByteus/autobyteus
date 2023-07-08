"""
This module contains a factory method for creating instances of storage backend classes.
Based on the configuration, this factory will instantiate the appropriate storage
backend (e.g., RedisStorage, WeaviateStorage) and return it.

Example:
    storage = create_storage() # Creates an instance of the storage backend as per configuration

"""
import weaviate
from src.semantic_code.storage.base_storage import BaseStorage
from src.config.config import config
from src.singleton import SingletonMeta
from src.source_code_tree.code_entities.base_entity import CodeEntity

class WeaviateStorage(BaseStorage):
    """
    WeaviateStorage is a concrete class that extends the BaseStorage class.
    This class is responsible for storing and retrieving embeddings in a Weaviate database.
    """

    def __init__(self, embedding_dim):
        """
        Initialize the WeaviateStorage class with a connection to Weaviate and create the schema if needed.

        :param embedding_dim: The dimensionality of the embeddings.
        :type embedding_dim: int
        """
        # Read configurations
        url = config.get('WEAVIATE_URL', default='http://localhost:8080')
        
        # Initialize Weaviate client
        self.client = weaviate.Client(url)
        self.embedding_dim = embedding_dim
        
        # TODO: Initialize schema for Weaviate if needed

    def store(self, key: str, entity: CodeEntity, embedding):
        # TODO: Store a CodeEntity and its embedding vector in Weaviate
        raise  NotImplemented()

    def retrieve(self, key: str):
        # TODO: Retrieve a CodeEntity from Weaviate
        raise  NotImplemented()

    def search(self, vector, top_k=5):
        # TODO: Search for the top_k closest code entities in Weaviate
        raise  NotImplemented()

    def close_connection(self):
        # TODO: Close the connection to Weaviate if necessary
        raise  NotImplemented()

