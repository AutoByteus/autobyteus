"""
index_service.py

This module contains the IndexService class, which is responsible for indexing code entities.
The IndexService utilizes embeddings created from code entities and stores them using a storage backend
retrieved by a get function.

Classes:
    - IndexService: Manages the indexing of code entities.
"""



from autobyteus.codeverse.core.code_entities.base_entity import CodeEntity
from autobyteus.storage.embedding.embedding_creator_factory import get_embedding_creator
from autobyteus.storage.embedding.storage.base_storage import BaseStorage
from autobyteus.storage.embedding.storage.storage_factory import get_storage
from autobyteus.utils.singleton import SingletonMeta


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
            If the entity has any children entities (e.g. a ModuleEntity having ClassEntities and FunctionEntities),
            it indexes those as well.

            Args:
                code_entity (CodeEntity): The code entity to be indexed.
            """
            try:
                self._index_entity(code_entity)
                if code_entity.children:
                    for child_entity in code_entity.children:
                        self._index_entity(child_entity)
            except Exception as e:
                raise RuntimeError(f"Failed to index code entity: {str(e)}")

    def _index_entity(self, code_entity: CodeEntity):
        """
        Helper method to index a single code entity.
        
        Args:
            code_entity (CodeEntity): The code entity to be indexed.
        """
        embedding = self.embedding_creator.create_embedding(code_entity.to_description())
        self.base_storage.store(code_entity.to_unique_id(), code_entity, embedding.tobytes())