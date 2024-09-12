"""
sentence_transformer_embedding_creator.py

This module contains the SentenceTransformerEmbeddingCreator class, which is responsible for creating embeddings
using the SentenceTransformer library. It inherits from the BaseEmbeddingCreator abstract base class and implements
the `create_embedding` method. The class uses a specific SentenceTransformer model to convert input text into a numerical
representation (embedding) which can be used by machine learning models.
"""

import os
import numpy as np
from sentence_transformers import SentenceTransformer
from autobyteus.embeding.base_embedding_creator import BaseEmbeddingCreator

class SentenceTransformerEmbeddingCreator(BaseEmbeddingCreator):
    """
    SentenceTransformerEmbeddingCreator is a concrete class that extends the BaseEmbeddingCreator class.
    This class is responsible for generating embeddings using the SentenceTransformer library.
    """

    def __init__(self):
        """
        Initialize the SentenceTransformerEmbeddingCreator class by setting the model name
        from an environment variable.
        """
        self.model_name = os.environ.get('DEFAULT_SENTENCE_TRANSFORMER_MODEL', 'sentence-transformers/all-mpnet-base-v2')
        self.model = SentenceTransformer(self.model_name)

    @property
    def embedding_dim(self):
        """
        This property returns the dimension of the embedding produced by SentenceTransformerEmbeddingCreator.
        """
        return int(os.environ.get('DEFAULT_SENTENCE_TRANSFORMER_MODEL_DIM', '768'))
    
    def create_embedding(self, text: str) -> np.ndarray:
        """
        Creates an embedding from the input text using the SentenceTransformer library.
        
        Parameters:
        text (str): The input text to be converted into an embedding.
        
        Returns:
        np.ndarray: An embedding in the form of a numerical array.
        """
        return self.model.encode(text)
