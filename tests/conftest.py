from pymongo import MongoClient
import pytest
import os
from repository_mongodb import MongoConfig
from sqlalchemy.orm import sessionmaker
from repository_sqlalchemy.database_config import DatabaseConfig
from repository_sqlalchemy.session_management import get_engine
from repository_sqlalchemy import Base, transaction
from autobyteus.prompt.storage.prompt_version_model import PromptVersionModel


'''
@pytest.fixture(scope="session")
def db_config():
    os.environ['DB_TYPE'] = 'postgresql'
    os.environ['DB_NAME'] = 'postgres'  # Default database name
    os.environ['DB_USER'] = 'postgres'  # Default username
    os.environ['DB_PASSWORD'] = 'mysecretpassword'  # Password set in Docker run command
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'  # Default PostgreSQL port
    return DatabaseConfig('postgresql')
'''

@pytest.fixture(scope="session")
def db_config():
    os.environ['DB_TYPE'] = 'sqlite'
    os.environ['DB_NAME'] = ':memory:'
    return DatabaseConfig('sqlite')

@pytest.fixture(scope="session")
def engine(db_config):
    return get_engine()

@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function", autouse=True)
def clean_table_data():
    with transaction() as session:
        yield
        session.rollback()

@pytest.fixture(scope="session")
def mongo_config():
    os.environ['MONGO_HOST'] = 'localhost'
    os.environ['MONGO_PORT'] = '27017'
    os.environ['MONGO_USERNAME'] = ''
    os.environ['MONGO_PASSWORD'] = ''
    #os.environ['MONGO_DATABASE'] = 'test_database'
    return MongoConfig()

@pytest.fixture(scope="session")
def mongo_client(mongo_config):
    client = MongoClient(mongo_config.get_connection_uri())
    yield client
    client.close()

@pytest.fixture(scope="session")
def mongo_database(mongo_client, mongo_config):
    return mongo_client[mongo_config.database]
