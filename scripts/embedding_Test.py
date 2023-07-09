# %%

import redis
import numpy as np
from sentence_transformers import SentenceTransformer
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query

r = redis.Redis(host="localhost", port=6379)
INDEX_NAME = "index"  # Vector Index Name
DOC_PREFIX = "doc:"  # RediSearch Key Prefix for the Index
VECTOR_DIMENSIONS = 768  # define vector dimensions for all-MiniLM-L6-v2

def create_index(vector_dimensions: int):
    try:
        # check to see if index exists
        r.ft(INDEX_NAME).info()
        print("Index already exists!")
    except:
        # schema
        schema = (
            TagField("tag"),  # Tag Field Name
            VectorField("vector",  # Vector Field Name
                        "FLAT", {  # Vector Index Type: FLAT or HNSW
                            "TYPE": "FLOAT32",  # FLOAT32 or FLOAT64
                            "DIM": vector_dimensions,  # Number of Vector Dimensions
                            "DISTANCE_METRIC": "COSINE",  # Vector Search Distance Metric
                        }
                        ),
        )
        # index Definition
        definition = IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.HASH)
        # create Index
        r.ft(INDEX_NAME).create_index(fields=schema, definition=definition)

# create the index
create_index(vector_dimensions=VECTOR_DIMENSIONS)

# Load the SentenceTransformer model
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')

texts = [
    "This is a function to add two numbers.",
    "This is a function to subtract numbers.",
    "This function multiply two numbers."
]

# Create Embeddings with SentenceTransformer
embeddings = model.encode(texts)

# Write to Redis
pipe = r.pipeline()
for i, embedding in enumerate(embeddings):
    pipe.hset(f"{DOC_PREFIX}{i}", mapping = {
        "vector": embedding.tobytes(),
        "content": texts[i],
        "tag": "sentence-transformer"
    })
res = pipe.execute()

# KNN query
query = (
    Query("*=>[KNN 2 @vector $vec as score]")
    .sort_by("score")
    .return_fields("content", "tag", "score")
    .paging(0, 2)
    .dialect(2)
)

query_embedding = model.encode('multiply numbers')

query_params = {"vec": query_embedding.tobytes()}
print(r.ft(INDEX_NAME).search(query, query_params).docs)

# %%
# %% import redis
import redis
import numpy as np
import openai
from redis.commands.search.field import TagField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query


r = redis.Redis(host="localhost", port=6379)
INDEX_NAME = "index"  # Vector Index Name
DOC_PREFIX = "doc:"  # RediSearch Key Prefix for the Index
VECTOR_DIMENSIONS = 1536  # define vector dimensions

def create_index(vector_dimensions: int):
    try:
        # check to see if index exists
        r.ft(INDEX_NAME).info()
        print("Index already exists!")
    except:
        # schema
        schema = (
            TagField("tag"),  # Tag Field Name
            VectorField("vector",  # Vector Field Name
                        "FLAT", {  # Vector Index Type: FLAT or HNSW
                            "TYPE": "FLOAT32",  # FLOAT32 or FLOAT64
                            "DIM": vector_dimensions,  # Number of Vector Dimensions
                            "DISTANCE_METRIC": "COSINE",  # Vector Search Distance Metric
                        }
                        ),
        )
        # index Definition
        definition = IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.HASH)
        # create Index
        r.ft(INDEX_NAME).create_index(fields=schema, definition=definition)

# create the index
create_index(vector_dimensions=VECTOR_DIMENSIONS)

# set your OpenAI API key - get one at https://platform.openai.com
openai.api_key = ""

texts = [
    "Today is a really great day!",
    "The dog next door barks really loudly.",
    "My cat escaped and got out before I could close the door.",
    "It's supposed to rain and thunder tomorrow."
]

response = openai.Embedding.create(input=texts, engine="text-embedding-ada-002")
embeddings = np.array([r["embedding"] for r in response["data"]], dtype=np.float32)

# Write to Redis
pipe = r.pipeline()
for i, embedding in enumerate(embeddings):
    pipe.hset(f"{DOC_PREFIX}{i}", mapping = {
        "vector": embedding.tobytes(),
        "content": texts[i],
        "tag": "openai"
    })
res = pipe.execute()

# KNN query
query = (
    Query("(@tag:{ openai })=>[KNN 2 @vector $vec as score]")
    .sort_by("score")
    .return_fields("content", "tag", "score")
    .paging(0, 2)
    .dialect(2)
)
query_params = {"vec": embeddings[0].tobytes()}
print(r.ft(INDEX_NAME).search(query, query_params).docs)
# %%
