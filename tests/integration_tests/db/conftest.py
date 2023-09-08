import pytest
from sqlalchemy import DateTime, Integer, create_engine, exc, func
from sqlalchemy import text
from autobyteus.config import config
from sqlalchemy import Column, String
from autobyteus.db.models.base_model import Base

@pytest.fixture(autouse=True)
def setup_and_teardown_postgres():
    """
    This fixture sets up a test PostgreSQL database before the test and drops it after the test.
    """
    # Backup current configurations
    old_username = config.get('DB_USERNAME', default='postgres')
    old_password = config.get('DB_PASSWORD', default='password')
    old_host = config.get('DB_HOST', default='localhost')
    old_port = config.get('DB_PORT', default='5432')
    old_db_name = config.get('DB_NAME', default='autobyteus')

    # Set new configurations for testing
    test_db_name = "autobyteus_test"
    config.set('DB_NAME', test_db_name)

    # Create a connection to the PostgreSQL server (not to a specific database)
    server_engine = create_engine(f"postgresql://{old_username}:{old_password}@{old_host}:{old_port}", isolation_level='AUTOCOMMIT')
    connection = server_engine.connect()

    # Replicating the create_database logic for PostgreSQL
    try:
        # Create the test database
        connection.execute(text(f"CREATE DATABASE {test_db_name}"))
    except Exception as e:  # Handle case where the database might already exist
        # Log or handle the exception if needed
        print(e)

    # Create a new engine connected to the test database
    test_db_engine = create_engine(f"postgresql://{old_username}:{old_password}@{old_host}:{old_port}/{test_db_name}")

    # Now, create tables in the test database
    Base.metadata.create_all(test_db_engine)

    # This is where the testing happens
    yield  

    # Replicating the drop_database logic
    try:
        Base.metadata.drop_all(test_db_engine)
        # Drop the test database
        connection.execute(text(f"DROP DATABASE {test_db_name}"))
    except Exception as e:  # Handle case where the database might not exist
        # Log or handle the exception if needed
        print(e)

    connection.close()  # Close the connection

    # Restore the old configurations
    config.set('DB_USERNAME', old_username)
    config.set('DB_PASSWORD', old_password)
    config.set('DB_HOST', old_host)
    config.set('DB_PORT', old_port)
    config.set('DB_NAME', old_db_name)
