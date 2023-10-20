"""
autobyteus/db/utils/database_session_manager.py

This module provides a context manager to manage database sessions for the AI coding agent application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import DatabaseError
from autobyteus.config import config
from autobyteus.utils.singleton import SingletonMeta


class DatabaseSessionManager(metaclass=SingletonMeta):
    """
    Context manager for managing database sessions.
    
    Provides functionality to manage sessions for CRUD operations, ensuring resource cleanup 
    and error handling.
    
    Attributes:
        session_factory: Callable factory function to produce new sessions.
    """

    def __init__(self, session_factory: callable = None):
        """
        Initialize the DatabaseSessionManager with the session factory.
        
        If no session factory is provided, it creates one dynamically by fetching the latest 
        database configurations. This ensures that any changes made to the configurations, 
        such as by test fixtures, are respected.
        
        Args:
            session_factory (callable, optional): Factory function to produce new sessions. 
                                                  Defaults to None.
        """
        # If no session factory is provided, create one dynamically
        if session_factory is None:
            # Fetching database connection details from the configuration
            DB_USERNAME = config.get('DB_USERNAME', default='postgres')
            DB_PASSWORD = config.get('DB_PASSWORD', default='password')
            DB_HOST = config.get('DB_HOST', default='localhost')
            DB_PORT = config.get('DB_PORT', default='5432')
            DB_NAME = config.get('DB_NAME', default='autobyteus')

            # Constructing the database URL
            DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            engine = create_engine(DATABASE_URL)
            
            # Creating the session factory, careful with expire_on_commit
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        
        self.engine = engine
        self.session_factory = session_factory
        self.session = None

    def __enter__(self) -> Session:
        """
        Enter the context and initialize the session.
        
        Returns:
            Session: Initialized session.
        """
        self.session = self.session_factory()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit the context, handle errors and close the session.
        
        Args:
            exc_type (Type[BaseException]): The type of the exception.
            exc_value (BaseException): The exception instance raised.
            traceback (TracebackType): A traceback object.
        """
        if exc_type is not None:
            # An exception occurred, rollback the session
            try:
                self.session.rollback()
            except DatabaseError:
                # Log or handle session rollback error if necessary
                pass

        # Close the session
        self.session.close()
