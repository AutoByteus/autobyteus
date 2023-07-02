import logging
import redis
from redis.commands.search.query import Query
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from src.semantic_code.storage.base_storage import BaseStorage
from src.config.config import config

logger = logging.getLogger(__name__)

class RedisStorage(BaseStorage):
    """
    RedisStorage is a concrete class that extends the BaseStorage class.
    This class is responsible for storing and retrieving embeddings in a Redis database.
    """

    def __init__(self):
        """
        Initialize the RedisStorage class with a connection to Redis and create an index if not already exists.
        """
        # Read configurations
        host = config.get('REDIS_HOST', default='localhost')
        port = config.get('REDIS_PORT', default=6379)
        db = config.get('REDIS_DB', default=0)

        # Initialize Redis connection
        self.redis_client = redis.Redis(host=host, port=port, db=db, encoding='utf-8', decode_responses=True)

        self._initialize_schema()

    def _initialize_schema(self):
        """
        Initialize the schema for the Redis database.
        """
        schema = [
            TextField("url"),
            VectorField("embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": 1536, "DISTANCE_METRIC": "COSINE"}),
        ]
        try:
            self.redis_client.ft("posts").create_index(fields=schema, definition=IndexDefinition(prefix=["post:"], index_type=IndexType.HASH))
        except Exception as e:
            logger.info("Index already exists")

    def store(self, key: str, vector):
        """
        Store an embedding vector associated with a key in Redis.

        :param key: The key associated with the embedding.
        :type key: str
        :param vector: The embedding vector.
        """
        post_hash = {
            "url": key,
            "embedding": vector
        }
        self.redis_client.hset(name=f"post:{key}", mapping=post_hash)

    def retrieve(self, query: str):
        """
        Retrieve an embedding vector associated with a key from Redis.

        :param key: The key associated with the embedding.
        :type key: str
        :return: The embedding vector.
        """
        return self.redis_client.hget(name=f"post:{key}", key="embedding")

    def search(self, vector, top_k=5):
        """
        Search for the top_k closest embeddings to the given vector in Redis.

        :param vector: The query embedding vector.
        :param top_k: The number of closest embeddings to retrieve. Defaults to 5.
        :return: The list of closest embedding vectors and associated keys.
        """
        base_query = f"*=>[KNN {top_k} @embedding $vector AS vector_score]"
        query = Query(base_query).return_fields("url", "vector_score").sort_by("vector_score").dialect(2)
        try:
            results = self.redis_client.ft("posts").search(query, query_params={"vector": vector})
        except Exception as e:
            logging.error(f"Error calling Redis search: {e}")
            return None
        return results

    def close_connection(self):
        """
        Close the connection to Redis.
        """
        self.redis_client.close()



