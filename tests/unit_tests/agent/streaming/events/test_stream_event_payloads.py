import pytest
from pydantic import ValidationError
from autobyteus.agent.streaming.events.stream_event_payloads import (
    ArtifactPersistedData,
    create_artifact_persisted_data,
    ArtifactUpdatedData,
    create_artifact_updated_data,
    AssistantChunkData,
    create_assistant_chunk_data,
    ToDoListUpdateData,
    create_todo_list_update_data,
    AgentStatusUpdateData,
    create_agent_status_update_data,
    ErrorEventData,
    create_error_event_data
)
from autobyteus.agent.status.status_enum import AgentStatus

# --- ArtifactPersistedData Tests ---

def test_artifact_persisted_data_creation_valid():
    """Test creating ArtifactPersistedData with valid fields."""
    data = {
        "artifact_id": "art_123",
        "path": "/tmp/file.txt",
        "agent_id": "agent_001",
        "type": "file"
    }
    payload = ArtifactPersistedData(**data)
    assert payload.artifact_id == "art_123"
    assert payload.path == "/tmp/file.txt"
    assert payload.agent_id == "agent_001"
    assert payload.type == "file"

def test_artifact_persisted_data_ignores_extra_fields():
    """Test that passing 'status' does not crash, but the field is ignored/not stored."""
    data = {
        "artifact_id": "art_123",
        "status": "saved", # Extra field
        "path": "/tmp/file.txt",
        "agent_id": "agent_001",
        "type": "file"
    }
    payload = ArtifactPersistedData(**data)
    assert payload.artifact_id == "art_123"
    # Extra fields are allowed on stream payloads
    assert payload.status == "saved"

def test_create_artifact_persisted_data_factory():
    """Test the factory function works correctly."""
    data = {
        "artifact_id": "art_123",
        "path": "/tmp/file.txt",
        "agent_id": "agent_001",
        "type": "file"
    }
    payload = create_artifact_persisted_data(data)
    assert isinstance(payload, ArtifactPersistedData)
    assert payload.path == "/tmp/file.txt"

def test_artifact_persisted_data_validation_error():
    """Test that missing mandatory fields still raise ValidationError."""
    data = {
        "artifact_id": "art_123",
        # "path": "missing", 
        "agent_id": "agent_001",
        "type": "file"
    }
    with pytest.raises(ValidationError) as excinfo:
        ArtifactPersistedData(**data)
    assert "path" in str(excinfo.value)

# --- ArtifactUpdatedData Tests ---

def test_artifact_updated_data_creation_valid():
    """Test creating ArtifactUpdatedData with valid fields."""
    data = {
        "path": "/tmp/file.txt",
        "agent_id": "agent_001",
        "type": "file"
    }
    payload = ArtifactUpdatedData(**data)
    assert payload.path == "/tmp/file.txt"
    assert payload.agent_id == "agent_001"
    assert payload.type == "file"

def test_create_artifact_updated_data_factory():
    """Test the factory function works correctly."""
    data = {
        "path": "/tmp/file.txt",
        "agent_id": "agent_001",
        "type": "file"
    }
    payload = create_artifact_updated_data(data)
    assert isinstance(payload, ArtifactUpdatedData)
    assert payload.path == "/tmp/file.txt"

# --- Other Payload Tests (Regression Checks) ---

def test_create_assistant_chunk_data_from_dict():
    """Test creating AssistantChunkData from a dictionary."""
    data = {"content": "Hello", "is_complete": False}
    payload = create_assistant_chunk_data(data)
    assert isinstance(payload, AssistantChunkData)
    assert payload.content == "Hello"
    assert payload.is_complete is False

def test_create_todo_list_update_data_valid():
    """Test creating ToDoListUpdateData with valid nested list."""
    data = {
        "todos": [
            {"description": "Task 1", "todo_id": "1", "status": "pending"},
            {"description": "Task 2", "todo_id": "2", "status": "done"}
        ]
    }
    payload = create_todo_list_update_data(data)
    assert isinstance(payload, ToDoListUpdateData)
    assert len(payload.todos) == 2
    assert payload.todos[0].description == "Task 1"

def test_create_todo_list_update_data_invalid_type():
    """Test validation error when 'todos' is not a list."""
    data = {"todos": "not a list"}
    with pytest.raises(ValueError, match="Expected 'todos' to be a list"):
        create_todo_list_update_data(data)

def test_create_agent_status_update_data():
    """Test creating AgentStatusUpdateData."""
    data = {"new_status": AgentStatus.IDLE}
    payload = create_agent_status_update_data(data)
    assert isinstance(payload, AgentStatusUpdateData)
    assert payload.new_status == AgentStatus.IDLE

def test_create_error_event_data():
    """Test creating ErrorEventData."""
    data = {"source": "test", "message": "error msg"}
    payload = create_error_event_data(data)
    assert isinstance(payload, ErrorEventData)
    assert payload.source == "test"
    assert payload.message == "error msg"
