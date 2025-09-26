import pytest
import os
from autobyteus.tools.multimedia.image_tools import GenerateImageTool, EditImageTool, _get_configured_model_identifier
from autobyteus.tools.parameter_schema import ParameterType

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set.")

@pytest.mark.parametrize("env_var", ["DEFAULT_IMAGE_GENERATION_model", "DEFAULT_IMAGE_EDIT_MODEL"])
def test_get_configured_model_identifier_success(env_var):
    """Tests that the helper function correctly reads the environment variable."""
    expected_model = os.getenv(env_var)
    if not expected_model:
        pytest.skip(f"Environment variable '{env_var}' is not set; skipping test.")
    assert _get_configured_model_identifier(env_var, "fallback") == expected_model

def test_get_configured_model_identifier_fallback():
    """Tests that the helper function correctly uses the fallback."""
    assert _get_configured_model_identifier("NON_EXISTENT_VAR", "fallback_model") == "fallback_model"

@pytest.mark.parametrize("env_var", ["DEFAULT_IMAGE_GENERATION_MODEL", "DEFAULT_IMAGE_EDIT_MODEL"])
def test_get_configured_model_identifier_failure(monkeypatch, env_var):
    """Tests that a ValueError is raised if the environment variable is not set and no fallback is provided."""
    monkeypatch.delenv(env_var, raising=False)
    with pytest.raises(ValueError, match="environment variable is not set"):
        _get_configured_model_identifier(env_var)

def test_generate_image_tool_dynamic_schema():
    """Tests that the GenerateImageTool's schema is generated dynamically and correctly."""
    tool = GenerateImageTool(config={})
    schema = tool.get_argument_schema()
    
    params_dict = {p.name: p for p in schema.parameters}

    assert "prompt" in params_dict
    assert "input_image_urls" in params_dict
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
async def test_generate_image_tool_execute():
    """Tests a successful execution of the GenerateImageTool."""
    tool = GenerateImageTool(config={})
    prompt = "A majestic lion standing on a rock at sunset, cartoon style"
    
    generation_config = {}
    
    result = await tool._execute(context={}, prompt=prompt, generation_config=generation_config)

    assert isinstance(result, list)
    assert len(result) > 0
    for url in result:
        assert isinstance(url, str)
        assert url.startswith("https://") or url.startswith("data:")

@pytest.mark.asyncio
async def test_generate_image_with_reference_tool_execute():
    """
    Tests generating an image using another generated image as a style reference.
    """
    # Step 1: Generate a base image to use as a reference.
    tool = GenerateImageTool(config={})
    base_prompt = "A simple, black and white, comic book style ink drawing of a superhero's face."
    
    base_urls = await tool._execute(context={}, prompt=base_prompt, generation_config={})
    assert isinstance(base_urls, list)
    assert len(base_urls) > 0
    reference_url = base_urls[0]
    assert isinstance(reference_url, str)
    print(f"Generated reference image URL: {reference_url}")

    # Step 2: Generate a new image using the first one as a reference.
    # Note: This heavily depends on the model's ability to interpret image inputs.
    # For Gemini, this works well. For DALL-E 3 via the images.generate API, it's ignored.
    # The test verifies the tool passes the parameter correctly.
    new_prompt = "A full-color comic book style image of Batman fighting the Joker, in the same art style as the reference image."
    
    new_urls = await tool._execute(
        context={},
        prompt=new_prompt,
        input_image_urls=reference_url,
        generation_config={}
    )

    assert isinstance(new_urls, list)
    assert len(new_urls) > 0
    new_url = new_urls[0]
    assert isinstance(new_url, str)
    assert new_url != reference_url
    assert new_url.startswith("https://") or new_url.startswith("data:")


def test_edit_image_tool_dynamic_schema():
    """Tests that the EditImageTool's schema is generated dynamically and correctly."""
    tool = EditImageTool(config={})
    schema = tool.get_argument_schema()
    
    params_dict = {p.name: p for p in schema.parameters}

    assert "prompt" in params_dict
    assert "input_image_urls" in params_dict
    assert "mask_image_url" in params_dict
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

@pytest.mark.asyncio
async def test_edit_image_tool_execute():
    """
    Tests a successful end-to-end execution of generating and then editing an image.
    """
    # Step 1: Generate an initial image
    generate_tool = GenerateImageTool(config={})
    generate_prompt = "A simple monarch butterfly on a white background, cartoon style"
    
    generated_urls = await generate_tool._execute(
        context={}, 
        prompt=generate_prompt, 
        generation_config={}
    )

    assert isinstance(generated_urls, list)
    assert len(generated_urls) > 0
    original_image_url = generated_urls[0]
    assert isinstance(original_image_url, str)
    print(f"Generated image URL for editing: {original_image_url}")
    # Step 2: Edit the generated image
    edit_tool = EditImageTool(config={})
    edit_prompt = "Add a tiny party hat on the butterfly's head"
    
    edited_urls = await edit_tool._execute(
        context={}, 
        prompt=edit_prompt, 
        input_image_urls=original_image_url, 
        generation_config={}
    )

    assert isinstance(edited_urls, list)
    assert len(edited_urls) > 0
    edited_image_url = edited_urls[0]
    assert isinstance(edited_image_url, str)
    
    # Verify that a new image was created
    assert edited_image_url != original_image_url
