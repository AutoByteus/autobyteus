"""
This module contains the WeaviateStorage class, which is a concrete implementation
of the BaseStorage class for interacting with a Weaviate database. The WeaviateStorage
class is responsible for storing and retrieving code entities and their embeddings
in a Weaviate database.

Example:
    storage = WeaviateStorage()
    storage.store(key="example", entity=CodeEntity(docstring="Example"), vector=[1.0, 2.0, 3.0])
    retrieved_entity = storage.retrieve(key="example")

"""
from src.config.config import config
from src.semantic_code.storage.redis_storage import RedisStorage
from src.semantic_code.storage.weaviate_storage import WeaviateStorage

def create_storage():
    """
    Factory method to create an instance of the appropriate storage backend class
    based on the configuration.
    
    :return: An instance of a storage backend class.
    """

    storage_backend = config.get('STORAGE_BACKEND', default='redis').lower()

    if storage_backend == 'redis':
        return RedisStorage()
    elif storage_backend == 'weaviate':
        return WeaviateStorage()
    else:
        raise ValueError(f"Invalid storage backend: {storage_backend}")
