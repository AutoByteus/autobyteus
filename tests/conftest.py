import pytest
import os
from sqlalchemy.orm import sessionmaker
from repository_sqlalchemy.database_config import DatabaseConfig
from repository_sqlalchemy.session_management import get_engine
from repository_sqlalchemy import Base

from autobyteus.storage.sql.models.prompt_version_model import PromptVersionModel


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