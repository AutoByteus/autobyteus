"""
milvus_storage.py

This module contains the MilvusStorage class, which is responsible for storing and retrieving
embeddings using Milvus vector database. It implements the BaseStorage interface and provides
methods for storing, retrieving, and searching vector embeddings.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any

from pymilvus import (
    connections,
    Collection,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType
)

from autobyteus.storage.embedding.storage.base_storage import BaseStorage

logger = logging.getLogger(__name__)

class MilvusStorage(BaseStorage):
    """
    MilvusStorage is a concrete class that extends the BaseStorage class.
    This class is responsible for storing and retrieving embeddings in a Milvus database.
    """

    def __init__(self, embedding_dim: int):
        """
        Initialize the MilvusStorage class with a connection to Milvus and create a collection if not exists.

        Args:
            embedding_dim (int): The dimensionality of the embeddings
        """
        self.embedding_dim = embedding_dim
        self.collection_name = os.environ.get('MILVUS_COLLECTION', 'code_entities')
        
        # Connect to Milvus
        host = os.environ.get('MILVUS_HOST', 'localhost')
        port = os.environ.get('MILVUS_PORT', '19530')
        
        try:
            connections.connect(
                alias="default",
                host=host,
                port=port
            )
            self._initialize_collection()
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {str(e)}")
            raise

    def _initialize_collection(self):
        """Initialize Milvus collection with the required schema."""
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=255, is_primary=True),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="representation", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
        ]

        schema = CollectionSchema(
            fields=fields,
            description="Code entities collection"
        )

        self.collection = Collection(
            name=self.collection_name,
            schema=schema,
            using='default'
        )

        # Create index for vector field
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024}
        }
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )

    def store(self, key: str, entity: Any, embedding):
        """
        Store a CodeEntity with its embedding vector in Milvus.

        Args:
            key (str): The unique identifier for the entity
            entity (Any): The code entity object
            embedding (numpy.ndarray): The embedding vector
        """
        try:
            data = [{
                "id": key,
                "type": entity.type.value,
                "representation": entity.to_json(),
                "embedding": embedding.tolist()
            }]
            
            self.collection.insert(data)
            self.collection.flush()
        except Exception as e:
            logger.error(f"Failed to store entity in Milvus: {str(e)}")
            raise

    def retrieve(self, key: str) -> Optional[Dict]:
        """
        Retrieve a code entity by its key from Milvus.

        Args:
            key (str): The unique identifier for the entity

        Returns:
            Optional[Dict]: The retrieved entity or None if not found
        """
        try:
            self.collection.load()
            results = self.collection.query(
                expr=f'id == "{key}"',
                output_fields=["id", "type", "representation", "embedding"]
            )
            self.collection.release()
            
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Failed to retrieve entity from Milvus: {str(e)}")
            raise

    def search(self, embedding, top_k=5):
        """
        Search for similar entities using vector similarity search.

        Args:
            embedding (numpy.ndarray): The query embedding vector
            top_k (int): Number of results to return

        Returns:
            List[Dict]: List of similar entities with their scores
        """
        try:
            self.collection.load()
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["id", "type", "representation"]
            )
            
            self.collection.release()
            
            return [
                {
                    "id": hit.entity.get("id"),
                    "type": hit.entity.get("type"),
                    "representation": hit.entity.get("representation"),
                    "score": hit.score
                }
                for hit in results[0]
            ]
        except Exception as e:
            logger.error(f"Failed to search in Milvus: {str(e)}")
            raise

    def flush_db(self):
        """Remove all entities from the collection."""
        try:
            if utility.has_collection(self.collection_name):
                utility.drop_collection(self.collection_name)
                self._initialize_collection()
        except Exception as e:
            logger.error(f"Failed to flush Milvus collection: {str(e)}")
            raise

    def close_connection(self):
        """Close the connection to Milvus."""
        try:
            connections.disconnect("default")
        except Exception as e:
            logger.error(f"Failed to close Milvus connection: {str(e)}")
            raise