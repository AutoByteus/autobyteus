"""
openai_embedding_creator.py

This module contains the OpenAIEmbeddingCreator class, which is responsible for creating embeddings
using OpenAI's API. It reads the API key and model name from a configuration file and utilizes
OpenAI's API to generate embeddings for the input text.
"""

import openai
import numpy as np
import logging
from src.semantic_code.embedding.base_embedding_creator import BaseEmbeddingCreator
from src.config import config
from src.singleton import ABCSingletonMeta

logger = logging.getLogger(__name__)

class OpenAIEmbeddingCreator(BaseEmbeddingCreator):
    """
    OpenAIEmbeddingCreator is a concrete class that extends the BaseEmbeddingCreator class.
    This class is responsible for generating embeddings using OpenAI's API.
    """

    def __init__(self):
        """
        Initialize the OpenAIEmbeddingCreator class by reading the API key and model name
        from the configuration file.
        """
        self.api_key = config.get('OPEN_AI_API_KEY')
        self.model_name = config.get('OPEN_AI_EMBEDDING_MODEL', default="text-embedding-ada-002")
        logger.info("OpenAIEmbeddingCreator using embedding model %s", self.model_name)

    @property
    def embedding_dim(self):
        """
        This property returns the dimension of the embedding produced by OpenAIEmbeddingCreator.
        """
        return config.get('OPEN_AI_EMBEDDING_MODEL.EMBEDDING_DIM', default=1536)  # for instance
    
    def create_embedding(self, text: str):
        """
        Create an embedding for the given text using OpenAI's API.
        
        Parameters:
        text (str): The input text for which the embedding should be generated.

        Returns:
        bytes: The embedding in bytes format.
        """
        logger.info("Creating embedding for text: %s", text)
        try:
            embedding = openai.Embedding.create(input=text, model=self.model_name)
            vector = embedding["data"][0]["embedding"]
            vector = np.array(vector).astype(np.float32).tobytes()
            logger.info("Embedding created successfully")
            return vector
        except Exception as e:
            logger.error("Failed to create embedding: %s", str(e))
            return None
