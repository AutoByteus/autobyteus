"""
sentence_transformer_embedding_creator.py

This module contains the SentenceTransformerEmbeddingCreator class, which is responsible for creating embeddings
using the SentenceTransformer library. It inherits from the BaseEmbeddingCreator abstract base class and implements
the `create_embedding` method. The class uses a specific SentenceTransformer model to convert input text into a numerical
representation (embedding) which can be used by machine learning models.
"""

from sentence_transformers import SentenceTransformer
from src.semantic_code.embedding.base_embedding_creator import BaseEmbeddingCreator

class SentenceTransformerEmbeddingCreator(BaseEmbeddingCreator):
    """
    SentenceTransformerEmbeddingCreator is a concrete class that extends the BaseEmbeddingCreator class.
    This class is responsible for generating embeddings using the SentenceTransformer library.
    """

    def __init__(self, model_name: str = 'sentence-transformers/all-mpnet-base-v2'):
        """
        Initialize the SentenceTransformerEmbeddingCreator class by setting the model name.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(self.model_name)

    def create_embedding(self, text: str):
        """
        Creates an embedding from the input text using the SentenceTransformer library.
        
        Parameters:
        text (str): The input text to be converted into an embedding.
        
        Returns:
        This method returns an embedding, usually in the form of a numerical array or tensor.
        """
        return self.model.encode([text])
