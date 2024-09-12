"""
This module contains the get_storage function which is responsible for getting instances of storage
classes based on a given configuration. It supports getting different types of storage classes,
such as RedisStorage and WeaviateStorage. Each type of storage class is implemented as a singleton,
ensuring only one instance of each type can exist.
"""

import os
from autobyteus.embeding.embedding_creator_factory import get_embedding_creator
from autobyteus.storage.embedding.storage.redis_storage import RedisStorage
from autobyteus.storage.embedding.storage.weaviate_storage import WeaviateStorage

def get_storage():
    """
    Factory method to get an instance of the appropriate storage backend class
    based on the environment variable. If the instance does not exist, it is created due to the singleton nature of the classes.
    
    :return: An instance of a storage backend class.
    """
    storage_backend = os.environ.get('STORAGE_BACKEND', 'redis').lower()

    if storage_backend == 'redis':
        return RedisStorage(get_embedding_creator().embedding_dim)
    elif storage_backend == 'weaviate':
        return WeaviateStorage(get_embedding_creator().embedding_dim)
    elif storage_backend == 'faiss':
        # TODO: Implement FAISS storage
        raise NotImplementedError("FAISS storage is not yet implemented")
    else:
        raise ValueError(f"Invalid storage backend: {storage_backend}")
