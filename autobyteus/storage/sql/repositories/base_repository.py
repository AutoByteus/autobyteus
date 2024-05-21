"""
autobyteus.db.repositories.base_repository
=========================================

This module provides a base repository structure that serves as a foundational module for interacting
with a PostgreSQL database using SQLAlchemy. It facilitates CRUD operations for the application.

This repository structure will be used by the AI coding agent and potentially other repositories in the future.
"""

from typing import List, Type, TypeVar, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from autobyteus.db.models.base_model import BaseModel
from autobyteus.db.utils.database_session_manager import DatabaseSessionManager

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository:
    """
    A generic repository class that provides CRUD operations with the help of SQLAlchemy.
    This class utilizes the DatabaseSessionManager for session management.
    """

    def __init__(self, session_manager: DatabaseSessionManager):
        """
        Initialize the repository with a session manager.

        Args:
            session_manager (DatabaseSessionManager): The session manager for database operations.
        """
        self.session_manager = session_manager

    def create(self, obj: ModelType) -> ModelType:
        """
        Create a new record in the database.

        Args:
            obj (ModelType): The object to be created.

        Returns:
            ModelType: The created object.
        """
        with self.session_manager as session:
            session.add(obj)
            session.commit()
            return obj

    def get(self, model_class: Type[ModelType], id: int) -> Optional[ModelType]:
        """
        Retrieve a record from the database by its ID.

        Args:
            model_class (Type[ModelType]): The model class of the object to be retrieved.
            id (int): The ID of the object to be retrieved.

        Returns:
            Optional[ModelType]: The retrieved object or None if not found.
        """
        with self.session_manager as session:
            return session.query(model_class).filter_by(id=id).first()

    def get_all(self, model_class: Type[ModelType]) -> List[ModelType]:
        """
        Retrieve all records of a specific model class from the database.

        Args:
            model_class (Type[ModelType]): The model class of the objects to be retrieved.

        Returns:
            List[ModelType]: A list of retrieved objects.
        """
        with self.session_manager as session:
            return session.query(model_class).all()

    def update(self, obj: ModelType, **kwargs) -> ModelType:
        """
        Update an existing record in the database.

        Args:
            obj (ModelType): The object to be updated.
            **kwargs: The fields to be updated with their new values.

        Returns:
            ModelType: The updated object.
        """
        with self.session_manager as session:
            for key, value in kwargs.items():
                setattr(obj, key, value)
            session.commit()
            return obj

    def delete(self, obj: ModelType):
        """
        Delete a record from the database.

        Args:
            obj (ModelType): The object to be deleted.
        """
        with self.session_manager as session:
            session.delete(obj)
            session.commit()

