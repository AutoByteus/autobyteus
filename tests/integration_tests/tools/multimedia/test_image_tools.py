import pytest
import os
from autobyteus.tools.multimedia.image_tools import GenerateImageTool, _get_configured_image_model_identifier
from autobyteus.tools.parameter_schema import ParameterType

TEST_MODEL_IDENTIFIER = "gpt-image-1"
TEST_IMAGEN_MODEL = "imagen-4-rpa@localhost" # Using local API model to avoid runtime dependency

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set.")

@pytest.fixture
def set_default_model_env(monkeypatch):
    """Sets the mandatory environment variable for the image tools."""
    monkeypatch.setenv("DEFAULT_IMAGE_GENERATION_MODEL", TEST_MODEL_IDENTIFIER)

@pytest.fixture
def set_imagen4_model_env(monkeypatch):
    """Sets the mandatory environment variable to imagen-4."""
    monkeypatch.setenv("DEFAULT_IMAGE_GENERATION_MODEL", TEST_IMAGEN_MODEL)

def test_get_configured_model_identifier_success(set_default_model_env):
    """Tests that the helper function correctly reads the environment variable."""
    assert _get_configured_image_model_identifier() == TEST_MODEL_IDENTIFIER

def test_get_configured_model_identifier_failure(monkeypatch):
    """Tests that a ValueError is raised if the environment variable is not set."""
    monkeypatch.delenv("DEFAULT_IMAGE_GENERATION_MODEL", raising=False)
    with pytest.raises(ValueError, match="environment variable is not set"):
        _get_configured_image_model_identifier()

def test_generate_image_tool_dynamic_schema(set_default_model_env):
    """Tests that the tool's schema is generated dynamically and correctly."""
    tool = GenerateImageTool(config={})
    schema = tool.get_argument_schema()
    
    params_dict = {p.name: p for p in schema.parameters}

    assert "prompt" in params_dict
    assert "generation_config" in params_dict
    config_param = params_dict["generation_config"]
    assert config_param.param_type == ParameterType.OBJECT
    
    object_schema = config_param.object_schema
    assert object_schema is not None
    assert object_schema["type"] == "object"
    
    properties = object_schema["properties"]
    assert "size" in properties
    assert "quality" in properties
    assert properties["size"]["default"] == "1024x1024"
    assert "1792x1024" in properties["size"]["enum"]

@pytest.mark.asyncio
async def test_generate_image_tool_execute(set_default_model_env):
    """Tests a successful execution of the GenerateImageTool with the gpt-image-1 model."""
    tool = GenerateImageTool(config={})
    prompt = "A cute, smiling capybara in a photorealistic style"
    
    generation_config = {
        "size": "1024x1024",
        "quality": "hd",
        "style": "vivid"
    }
    
    result = await tool._execute(context={}, prompt=prompt, generation_config=generation_config)

    assert isinstance(result, str)
    assert "Image generation successful. URLs:" in result
    assert "https://" in result

@pytest.mark.asyncio
async def test_generate_image_tool_execute_imagen4(set_imagen4_model_env):
    """Tests a successful execution of the GenerateImageTool with the imagen-4 model."""
    tool = GenerateImageTool(config={})
    prompt = "A majestic lion standing on a rock at sunset, cartoon style"
    
    # imagen-4 client doesn't have specific generation config from the factory
    generation_config = {}
    
    result = await tool._execute(context={}, prompt=prompt, generation_config=generation_config)

    assert isinstance(result, str)
    assert "Image generation successful. URLs:" in result
    print(result)
