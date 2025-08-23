import pytest
import os
from autobyteus.tools.multimedia.image_tools import GenerateImageTool, EditImageTool, _get_configured_model_identifier
from autobyteus.tools.parameter_schema import ParameterType

# Define the model to be used for testing.
TEST_MODEL_IDENTIFIER = "gpt-image-1"

@pytest.fixture(scope="module")
def check_api_keys():
    """Skips tests in this module if required API keys are not set."""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set. Skipping multimedia tool tests.")

@pytest.fixture
def set_default_model_env(monkeypatch):
    """Sets the mandatory environment variable for the image tools."""
    monkeypatch.setenv("DEFAULT_IMAGE_GENERATION_MODEL", TEST_MODEL_IDENTIFIER)

def test_get_configured_model_identifier_success(set_default_model_env):
    """Tests that the helper function correctly reads the environment variable."""
    assert _get_configured_model_identifier() == TEST_MODEL_IDENTIFIER

def test_get_configured_model_identifier_failure(monkeypatch):
    """Tests that a ValueError is raised if the environment variable is not set."""
    monkeypatch.delenv("DEFAULT_IMAGE_GENERATION_MODEL", raising=False)
    with pytest.raises(ValueError, match="environment variable is not set"):
        _get_configured_model_identifier()

def test_generate_image_tool_dynamic_schema(set_default_model_env):
    """Tests that the tool's schema is generated dynamically and correctly."""
    tool = GenerateImageTool(config={})
    schema = tool.get_argument_schema()

    # Convert the list of parameters to a dictionary for easy access by name
    params_dict = {p.name: p for p in schema.parameters}

    # Check for the static parameter
    assert "prompt" in params_dict
    
    # Check for the dynamic, nested config parameter
    assert "generation_config" in params_dict
    config_param = params_dict["generation_config"]
    assert config_param.param_type == ParameterType.OBJECT
    assert config_param.required is True
    
    # Check the nested schema for model-specific parameters
    object_schema = config_param.object_schema
    assert object_schema is not None
    assert object_schema["type"] == "object"
    
    properties = object_schema["properties"]
    assert "size" in properties
    assert "quality" in properties
    assert "style" in properties
    assert properties["size"]["default"] == "1024x1024"
    assert "1792x1024" in properties["size"]["enum"]

@pytest.mark.asyncio
async def test_generate_image_tool_execute(check_api_keys, set_default_model_env):
    """Tests a successful execution of the GenerateImageTool with the new signature."""
    tool = GenerateImageTool(config={})
    prompt = "A cute, smiling capybara in a photorealistic style"
    
    # Define a generation_config that overrides some defaults
    generation_config = {
        "size": "1024x1024", # Use a valid size for the model
        "quality": "hd",
        "style": "vivid"
    }
    
    result = await tool._execute(context={}, prompt=prompt, generation_config=generation_config)

    assert isinstance(result, str)
    print(result)
    assert "Image generation successful. URLs:" in result
    assert "https://" in result
