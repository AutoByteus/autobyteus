"""
This module contains the get_storage function which is responsible for getting instances of storage
classes based on a given configuration. It supports getting different types of storage classes,
such as RedisStorage and WeaviateStorage. Each type of storage class is implemented as a singleton,
ensuring only one instance of each type can exist.
"""

from autobyteus.config import config
from autobyteus.embeding.embedding_creator_factory import get_embedding_creator
from autobyteus.storage.embedding.storage.redis_storage import RedisStorage
from autobyteus.storage.embedding.storage.weaviate_storage import WeaviateStorage

def get_storage():
    """
    Factory method to get an instance of the appropriate storage backend class
    based on the configuration. If the instance does not exist, it is created due to the singleton nature of the classes.
    
    :return: An instance of a storage backend class.
    """
    storage_backend = config.get('STORAGE_BACKEND', default='redis').lower()

    if storage_backend == 'redis':
        return RedisStorage(get_embedding_creator().embedding_dim)
    elif storage_backend == 'weaviate':
        return WeaviateStorage(get_embedding_creator().embedding_dim)
    elif storage_backend == 'FAISS':
        pass
    else:
        raise ValueError(f"Invalid storage backend: {storage_backend}")
