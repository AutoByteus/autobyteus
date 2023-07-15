import logging
import numpy as np
import redis
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from src.semantic_code.storage.base_storage import BaseStorage
from src.config import config
from src.singleton import SingletonMeta
from src.source_code_tree.code_entities.base_entity import CodeEntity

logger = logging.getLogger(__name__)

class RedisStorage(BaseStorage):
    """
    RedisStorage is a concrete class that extends the BaseStorage class.
    This class is responsible for storing and retrieving embeddings in a Redis database.
    """
    def __init__(self, embedding_dim):
        """
        Initialize the RedisStorage class with a connection to Redis and create an index if not already exists.

        :param embedding_dim: The dimensionality of the embeddings.
        :type embedding_dim: int
        """
        # Read configurations
        host = config.get('REDIS_HOST', default='localhost')
        port = config.get('REDIS_PORT', default=6379)
        db = config.get('REDIS_DB', default=0)

        # Initialize Redis connection
        self.redis_client = redis.Redis(host=host, port=port, db=db, encoding='utf-8', decode_responses=True)

        self._initialize_schema(embedding_dim)

    def _initialize_schema(self, embedding_dim):
        """
        Initialize the schema for the Redis database.

        :param embedding_dim: The dimensionality of the embeddings.
        :type embedding_dim: int
        """
        schema = [
            TextField("id"),  
            TextField("type"),
            TextField("representation"), 
            VectorField("embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": embedding_dim, "DISTANCE_METRIC": "COSINE"}),
        ]
        try:
            self.redis_client.ft("code_entities").create_index(fields=schema, definition=IndexDefinition(prefix=["code_entity:"], index_type=IndexType.HASH))
        except Exception as e:
            logger.info("Index already exists")

    def store(self, key: str, entity: CodeEntity, embedding):
        """
        Store a CodeEntity with its embedding vector associated with a key in Redis.

        :param key: The key associated with the code entity.
        :type key: str
        :param entity: The code entity.
        :type entity: CodeEntity
        :param embedding: The embedding vector.
        """
        code_entity_fields = {
            "id": key,
            "type": entity.type.value,
            "representation": entity.to_json(),
            "embedding": embedding
        }
        self.redis_client.hset(name=f"code_entity:{key}", mapping=code_entity_fields)


    def retrieve(self, key: str):
        """
        Retrieve a code entity associated with a key from Redis.

        :param key: The key associated with the code entity.
        :type key: str
        :return: The code entity and its embedding vector.
        """
        entity_hash = self.redis_client.hgetall(name=f"code_entity:{key}")
        return entity_hash

    def search(self, embedding, top_k=5):
        """
        Search for the top_k closest code entities to the given vector in Redis.

        :param vector: The query embedding vector.
        :param top_k: The number of closest code entities to retrieve. Defaults to 5.
        :return: The list of closest code entities and associated keys.
        """
        base_query = f"*=>[KNN {top_k} @embedding $vector AS score]"
        query = Query(base_query).return_fields("id", "type", "representation", "score").sort_by("score").dialect(2)
        try:
            results = self.redis_client.ft("code_entities").search(query, query_params={"vector": embedding})
        except Exception as e:
            logging.error(f"Error calling Redis search: {e}")
            return None
        return results

    def flush_db(self):
        """
        Flushes the Redis database, removing all stored embeddings.
        """
        self.redis_client.flushdb()

    def close_connection(self):
        """
        Close the connection to Redis.
        """
        self.redis_client.close()
