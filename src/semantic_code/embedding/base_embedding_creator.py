"""
File Path: src/source_code_tree/code_entities/base_embedding_creator.py

This module defines the BaseEmbeddingCreator abstract base class which serves
as the base class for all embedding creators. Embedding creators are classes
responsible for converting text into a numerical representation (embedding)
that can be fed into machine learning models. This base class ensures that
all embedding creator subclasses have a consistent interface by enforcing
the implementation of the `create_embedding` method.
"""

from abc import ABC, abstractmethod

class BaseEmbeddingCreator(ABC):
    """
    This is an abstract base class that defines the interface for embedding
    creator classes. Classes inheriting from BaseEmbeddingCreator must
    implement the `create_embedding` method.
    
    Embedding creators are classes that convert input text into a numerical
    representation (embedding) which can be used by machine learning models.
    """

    @abstractmethod
    def create_embedding(self, text: str):
        """
        Creates an embedding from the input text.
        
        This is an abstract method and must be implemented by subclasses
        of BaseEmbeddingCreator.
        
        Parameters:
        text (str): The input text to be converted into an embedding.
        
        Returns:
        This method should return an embedding, usually in the form of a
        numerical array or tensor.
        """
        pass

