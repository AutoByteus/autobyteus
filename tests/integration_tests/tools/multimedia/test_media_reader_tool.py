import pytest
import os
import logging
from pathlib import Path
from PIL import Image

# Imports for the tool and its dependencies
from autobyteus.tools.multimedia.media_reader_tool import ReadMediaFile
from autobyteus.agent.message.context_file import ContextFile, ContextFileType
from autobyteus.agent.workspace.base_workspace import BaseAgentWorkspace
from autobyteus.agent.context import AgentContext, AgentRuntimeState, AgentConfig
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.utils.parameter_schema import ParameterSchema
from autobyteus.llm.utils.response_types import CompleteResponse, ChunkResponse

# Setup logger
logger = logging.getLogger(__name__)

# --- Corrected Mock Components for Testing ---

class MockWorkspace(BaseAgentWorkspace):
    """A mock workspace that uses a temporary directory and implements all abstract methods."""
    def __init__(self, base_path: Path):
        super().__init__()
        self._base_path = base_path

    def get_base_path(self) -> str:
        return str(self._base_path)
    
    @classmethod
    def get_workspace_type_name(cls) -> str: 
        return "mock_workspace"

    @classmethod
    def get_description(cls) -> str: 
        return "A mock workspace for testing purposes."

    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        return ParameterSchema()

class MockLLM(BaseLLM):
    """A correct mock LLM that satisfies the BaseLLM abstract class contract."""
    def __init__(self):
        # Create a mock model definition required by the BaseLLM constructor
        mock_model_def = LLMModel(
            name="mock-model",
            value="mock-model-v1",
            provider=LLMProvider.OPENAI, # Any provider is fine for a mock
            llm_class=MockLLM,
            canonical_name="mock-model",
            default_config=LLMConfig()
        )
        super().__init__(model=mock_model_def, llm_config=LLMConfig())

    # Implement the abstract methods from BaseLLM
    async def _send_user_message_to_llm(self, user_message):
        return CompleteResponse(content="mock response")

    async def _stream_user_message_to_llm(self, user_message):
        yield ChunkResponse(content="mock response", is_complete=True)

# --- Pytest Fixture ---

@pytest.fixture
def workspace_with_image(tmp_path: Path):
    """
    Creates a mock workspace in a temporary directory and places a dummy image file inside it.
    """
    # Create a dummy 1x1 pixel black image
    image_path = tmp_path / "test_image.png"
    img = Image.new('RGB', (1, 1), 'black')
    img.save(image_path, 'PNG')

    # Create a mock workspace pointing to this temp directory
    workspace = MockWorkspace(base_path=tmp_path)
    
    # Create a dummy AgentContext using the corrected mocks
    config = AgentConfig(
        name="test-agent", 
        role="tester", 
        description="An agent for testing", 
        llm_instance=MockLLM(), 
        workspace=workspace
    )
    state = AgentRuntimeState(agent_id="test-agent-123", workspace=workspace)
    context = AgentContext(agent_id="test-agent-123", config=config, state=state)

    yield {
        "context": context,
        "image_path": image_path,
        "workspace_root": tmp_path
    }

# --- Test Cases ---

@pytest.mark.asyncio
async def test_read_media_file_relative_path_success(workspace_with_image):
    """
    Tests successfully reading a media file using a workspace-relative path.
    """
    tool = ReadMediaFile()
    context = workspace_with_image["context"]
    image_path: Path = workspace_with_image["image_path"]

    # Use a relative path from the workspace root
    relative_path = image_path.name
    
    result = await tool._execute(context, file_path=relative_path)

    assert isinstance(result, ContextFile)
    assert result.uri == str(image_path.resolve())
    assert result.file_name == image_path.name
    assert result.file_type == ContextFileType.IMAGE
    logger.info(f"Successfully read file via relative path. Result: {result}")

@pytest.mark.asyncio
async def test_read_media_file_absolute_path_success(workspace_with_image):
    """
    Tests successfully reading a media file using an absolute path.
    """
    tool = ReadMediaFile()
    context = workspace_with_image["context"]
    image_path: Path = workspace_with_image["image_path"]

    # Use the absolute path
    absolute_path = str(image_path.resolve())
    
    result = await tool._execute(context, file_path=absolute_path)

    assert isinstance(result, ContextFile)
    assert result.uri == absolute_path
    assert result.file_name == image_path.name
    assert result.file_type == ContextFileType.IMAGE
    logger.info(f"Successfully read file via absolute path. Result: {result}")

@pytest.mark.asyncio
async def test_read_media_file_not_found(workspace_with_image):
    """
    Tests that the tool raises FileNotFoundError for a non-existent file.
    """
    tool = ReadMediaFile()
    context = workspace_with_image["context"]

    with pytest.raises(FileNotFoundError) as excinfo:
        await tool._execute(context, file_path="non_existent_file.jpg")
    
    assert "does not exist" in str(excinfo.value)
    logger.info("Correctly raised FileNotFoundError for non-existent file.")

@pytest.mark.asyncio
async def test_read_media_file_path_traversal_security(workspace_with_image):
    """
    Tests that the tool raises a ValueError for a path traversal attempt.
    """
    tool = ReadMediaFile()
    context = workspace_with_image["context"]

    # Attempt to access a file outside the workspace
    malicious_path = "../some_other_file.txt"

    with pytest.raises(ValueError) as excinfo:
        await tool._execute(context, file_path=malicious_path)

    assert "attempts to access files outside the agent's workspace" in str(excinfo.value)
    logger.info("Correctly raised ValueError for path traversal attempt.")
