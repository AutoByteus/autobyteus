# file: autobyteus/tests/unit_tests/tools/task_management/test_manage_artifact.py
import pytest
from unittest.mock import Mock

from autobyteus.agent.context import AgentContext
from autobyteus.agent_team.context import AgentTeamContext, AgentTeamRuntimeState
from autobyteus.task_management.tools import ManageArtifact
from autobyteus.task_management.artifacts import ArtifactManifest, ArtifactType, ArtifactState
from autobyteus.tools.registry import default_tool_registry

TOOL_NAME = "ManageArtifact"

@pytest.fixture
def tool_instance() -> ManageArtifact:
    return ManageArtifact()

@pytest.fixture
def mock_agent_context() -> AgentContext:
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_manage_artifact"
    mock_context.config = Mock()
    mock_context.config.name = "ArtifactAgent"
    mock_context.custom_data = {}
    return mock_context

@pytest.fixture
def mock_team_context() -> AgentTeamContext:
    """Provides a mock AgentTeamContext with a real dict for the artifact registry."""
    mock_context = Mock(spec=AgentTeamContext)
    mock_state = Mock(spec=AgentTeamRuntimeState)
    mock_state.artifact_registry = {}  # Use a real dictionary for testing state changes
    mock_context.state = mock_state
    return mock_context

def test_definition():
    """Tests the tool's definition and argument schema."""
    definition = default_tool_registry.get_tool_definition(TOOL_NAME)
    assert definition is not None
    assert definition.name == TOOL_NAME
    assert "Creates a new artifact or updates an existing one" in definition.description

@pytest.mark.asyncio
async def test_execute_create_new_artifact_success(tool_instance: ManageArtifact, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests successful creation of a new artifact."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    artifact_details = {
        "name": "My New Code",
        "description": "A Python script.",
        "artifact_type": ArtifactType.CODE.value,
        "state": ArtifactState.IN_PROGRESS.value,
        "file_manifest": ["src/main.py"]
    }
    
    # Act
    result = await tool_instance.execute(mock_agent_context, **artifact_details)
    
    # Assert
    assert "Successfully created new artifact 'My New Code'" in result
    
    # Check that the artifact was added to the registry
    assert len(mock_team_context.state.artifact_registry) == 1
    new_artifact_id = list(mock_team_context.state.artifact_registry.keys())[0]
    new_artifact = mock_team_context.state.artifact_registry[new_artifact_id]
    
    assert isinstance(new_artifact, ArtifactManifest)
    assert new_artifact.name == "My New Code"
    assert new_artifact.creator_agent_name == "ArtifactAgent"
    assert new_artifact.state == ArtifactState.IN_PROGRESS
    assert new_artifact.file_manifest == ["src/main.py"]

@pytest.mark.asyncio
async def test_execute_create_artifact_missing_required_args(tool_instance: ManageArtifact, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests that creation fails if name or type is missing."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    # Act & Assert
    result1 = await tool_instance.execute(mock_agent_context, description="Missing name and type")
    assert "Error: 'name' and 'artifact_type' are required" in result1
    
    result2 = await tool_instance.execute(mock_agent_context, name="Just a name")
    assert "Error: 'name' and 'artifact_type' are required" in result2

@pytest.mark.asyncio
async def test_execute_update_existing_artifact_success(tool_instance: ManageArtifact, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests successful update of an existing artifact."""
    # Arrange
    existing_id = "art_existing_123"
    existing_artifact = ArtifactManifest(
        artifact_id=existing_id,
        name="Old Name",
        description="Old description",
        artifact_type=ArtifactType.CODE,
        creator_agent_name="OriginalAgent"
    )
    mock_team_context.state.artifact_registry[existing_id] = existing_artifact
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    update_details = {
        "artifact_id": existing_id,
        "description": "New updated description",
        "state": ArtifactState.COMPLETED.value
    }
    
    # Act
    result = await tool_instance.execute(mock_agent_context, **update_details)
    
    # Assert
    assert f"Successfully updated artifact 'Old Name' (ID: {existing_id})" in result
    
    updated_artifact = mock_team_context.state.artifact_registry[existing_id]
    assert updated_artifact.description == "New updated description"
    assert updated_artifact.state == ArtifactState.COMPLETED
    assert updated_artifact.name == "Old Name" # Name was not updated
    assert updated_artifact.updated_at > updated_artifact.created_at

@pytest.mark.asyncio
async def test_execute_update_non_existent_artifact(tool_instance: ManageArtifact, mock_agent_context: AgentContext, mock_team_context: AgentTeamContext):
    """Tests failure when trying to update an artifact that doesn't exist."""
    # Arrange
    mock_agent_context.custom_data["team_context"] = mock_team_context
    
    # Act
    result = await tool_instance.execute(mock_agent_context, artifact_id="art_fake_456", state=ArtifactState.COMPLETED.value)
    
    # Assert
    assert "Error: Artifact with ID 'art_fake_456' not found" in result
