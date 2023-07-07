"""
embedding_creator_factory.py

This module contains the EmbeddingCreatorFactory class, which is responsible for creating instances of embedding
creator classes based on a given configuration. The factory supports the creation of different types of embedding
creators, such as OpenAIEmbeddingCreator and SentenceTransformerEmbeddingCreator.
"""

from src.semantic_code.embedding.base_embedding_creator import BaseEmbeddingCreator
from src.semantic_code.embedding.openai_embedding_creator import OpenAIEmbeddingCreator
from src.semantic_code.embedding.sentence_transformer_embedding_creator import SentenceTransformerEmbeddingCreator
from src.config.config import config

class EmbeddingCreatorFactory:
    """
    EmbeddingCreatorFactory is a factory class for creating instances of embedding creator classes.
    """

    @staticmethod
    def create_embedding_creator() -> BaseEmbeddingCreator:
        """
        Creates an instance of an embedding creator class based on the configuration.

        Returns:
        An instance of an embedding creator class.
        """
        embedding_type = config.get('DEFAULT_EMBEDDING_TYPE', 'sentence_transformer')
        if embedding_type == 'openai':
            return OpenAIEmbeddingCreator()
        elif embedding_type == 'sentence_transformer':
            model_name = config.get('DEFAULT_SENTENCE_TRANSFORMER_MODEL', 'sentence-transformers/all-mpnet-base-v2')
            return SentenceTransformerEmbeddingCreator(model_name=model_name)
        else:
            raise ValueError(f"Unsupported embedding type: {embedding_type}")
