# tests/integration_tests/db/repositories/test_base_repository_integration.py

import pytest
from sqlalchemy import Column, String
from sqlalchemy.orm import Session
from autobyteus.db.models.base_model import BaseModel
from autobyteus.db.repositories.base_repository import BaseRepository
from autobyteus.db.utils.database_session_manager import DatabaseSessionManager
    
class TestModel(BaseModel):  
    __tablename__ = 'test_model'
    name = Column(String)

@pytest.fixture
def base_repository() -> BaseRepository:
    """Fixture to provide a BaseRepository instance using the test database configuration."""
    session_manager = DatabaseSessionManager()  # It will use the test database configuration set by setup_and_teardown_postgres
    return BaseRepository(session_manager)

@pytest.fixture(autouse=True)
def cleanup_test_data(base_repository):
    """Fixture to clean up test data after each test."""
    yield  # Let the test run
    # Cleanup code after the test
    for obj in base_repository.get_all(TestModel):
        base_repository.delete(obj)

def test_given_object_when_created_then_saved_in_database(base_repository: BaseRepository):
    # Given: A sample object
    test_obj = TestModel(name="Test")
    
    # When: The object is added to the database
    created_obj = base_repository.create(test_obj)
    
    # Then: The object should be saved in the database with an ID assigned
    assert created_obj.id is not None
    assert created_obj.name == "Test"

def test_given_object_id_when_retrieved_then_correct_object_returned(base_repository: BaseRepository):
    # Given: A sample object saved in the database
    test_obj = TestModel(name="RetrieveTest")
    saved_obj = base_repository.create(test_obj)
    
    # When: The object is retrieved by its ID
    retrieved_obj = base_repository.get(TestModel, saved_obj.id)
    
    # Then: The correct object should be returned
    assert retrieved_obj.id == saved_obj.id
    assert retrieved_obj.name == "RetrieveTest"

def test_when_all_objects_retrieved_then_correct_objects_returned(base_repository):
    # Given: Multiple objects saved in the database
    obj1 = TestModel(name="Test1")
    obj2 = TestModel(name="Test2")
    base_repository.create(obj1)
    base_repository.create(obj2)
    
    # When: All objects are retrieved
    all_objects = base_repository.get_all(TestModel)

    # Then: All saved objects should be returned
    assert len(all_objects) >= 2
    names = [obj.name for obj in all_objects]
    assert "Test1" in names
    assert "Test2" in names

def test_given_object_when_updated_then_changes_reflected_in_database(base_repository):
    # Given: A sample object saved in the database
    test_obj = TestModel(name="OriginalName")
    saved_obj = base_repository.create(test_obj)
    
    # When: The object's name is updated
    updated_obj = base_repository.update(saved_obj, name="UpdatedName")
    
    # Then: The changes should be reflected in the database
    assert updated_obj.name == "UpdatedName"
    retrieved_obj = base_repository.get(TestModel, saved_obj.id)
    assert retrieved_obj.name == "UpdatedName"

def test_given_object_when_deleted_then_no_longer_in_database(base_repository):
    # Given: A sample object saved in the database
    test_obj = TestModel(name="ToDelete")
    saved_obj = base_repository.create(test_obj)
    
    # When: The object is deleted
    base_repository.delete(saved_obj)
    
    # Then: The object should no longer be present in the database
    retrieved_obj = base_repository.get(TestModel, saved_obj.id)
    assert retrieved_obj is None
