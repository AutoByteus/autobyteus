import pytest
import os
from pathlib import Path
from types import SimpleNamespace
from autobyteus.tools.multimedia.image_tools import GenerateImageTool, EditImageTool, _get_configured_model_identifier
from autobyteus.utils.parameter_schema import ParameterType, ParameterSchema, ParameterDefinition

class _MockWorkspace:
    def __init__(self, base_path: Path):
        self._base_path = base_path

    def get_base_path(self) -> str:
        return str(self._base_path)

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set.")
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set.")

@pytest.fixture(autouse=True)
def fix_models(monkeypatch):
    """Force valid model names for integration tests."""
    monkeypatch.setenv("DEFAULT_IMAGE_GENERATION_MODEL", "gemini-2.5-flash-image")
    monkeypatch.setenv("DEFAULT_IMAGE_EDIT_MODEL", "gemini-2.5-flash-image")

@pytest.mark.parametrize("env_var", ["DEFAULT_IMAGE_GENERATION_MODEL", "DEFAULT_IMAGE_EDIT_MODEL"])
def test_get_configured_model_identifier_success(monkeypatch, env_var):
    """Tests that the helper function correctly reads the environment variable."""
    monkeypatch.setenv(env_var, "test-model")
    assert _get_configured_model_identifier(env_var, "fallback") == "test-model"

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
    tool = GenerateImageTool()
    schema = tool.get_argument_schema()
    
    params_dict = {p.name: p for p in schema.parameters}

    assert "prompt" in params_dict
    assert "input_images" in params_dict
    assert "generation_config" in params_dict
    
    config_param = params_dict["generation_config"]
    assert config_param.param_type == ParameterType.OBJECT
    
    object_schema = config_param.object_schema
    assert isinstance(object_schema, ParameterSchema)
    
    size_param = object_schema.get_parameter("size")
    quality_param = object_schema.get_parameter("quality")

    assert isinstance(size_param, ParameterDefinition)
    assert size_param.default_value == "1024x1024"
    assert "1792x1024" in size_param.enum_values

    assert isinstance(quality_param, ParameterDefinition)
    assert quality_param.default_value == "auto"
    assert "high" in quality_param.enum_values


@pytest.mark.asyncio
async def test_generate_image_tool_execute(tmp_path):
    """Tests a successful execution of the GenerateImageTool."""
    tool = GenerateImageTool()
    prompt = "A majestic lion standing on a rock at sunset, cartoon style"
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))
    result = await tool.execute(context, prompt=prompt, generation_config={}, output_file_path="lion.png")

    assert isinstance(result, dict)
    assert "file_path" in result
    saved_path = Path(result["file_path"])
    assert saved_path.exists()
    assert saved_path.name == "lion.png"

@pytest.mark.asyncio
async def test_generate_image_with_reference_tool_execute(tmp_path):
    """
    Tests generating an image using another generated image as a style reference.
    """
    # Step 1: Generate a base image to use as a reference.
    tool = GenerateImageTool()
    base_prompt = "A simple black and white ink drawing of a smiling robot head."
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))

    base_result = await tool.execute(context, prompt=base_prompt, generation_config={}, output_file_path="base.png")
    reference_path = base_result["file_path"]
    print(f"Generated reference image path: {reference_path}")

    # Step 2: Generate a new image using the first one as a reference.
    # Note: This heavily depends on the model's ability to interpret image inputs.
    # For Gemini, this works well. For DALL-E 3 via the images.generate API, it's ignored.
    # The test verifies the tool passes the parameter correctly.
    new_prompt = "A full-color comic book style image of a friendly robot, in the same art style as the reference image."
    
    new_result = await tool.execute(
        context,
        prompt=new_prompt,
        input_images=reference_path,
        generation_config={},
        output_file_path="new.png"
    )

    new_path = new_result["file_path"]
    assert new_path != reference_path
    assert Path(new_path).exists()


def test_edit_image_tool_dynamic_schema():
    """Tests that the EditImageTool's schema is generated dynamically and correctly."""
    tool = EditImageTool()
    schema = tool.get_argument_schema()
    
    params_dict = {p.name: p for p in schema.parameters}

    assert "prompt" in params_dict
    assert "input_images" in params_dict
    assert "mask_image" in params_dict
    assert "generation_config" in params_dict
    
    config_param = params_dict["generation_config"]
    assert config_param.param_type == ParameterType.OBJECT
    
    object_schema = config_param.object_schema
    assert isinstance(object_schema, ParameterSchema)
    
    size_param = object_schema.get_parameter("size")
    assert isinstance(size_param, ParameterDefinition)
    assert size_param.default_value == "1024x1024"

@pytest.mark.asyncio
async def test_edit_image_tool_execute(tmp_path):
    """
    Tests a successful end-to-end execution of generating and then editing an image.
    """
    # Step 1: Generate an initial image
    generate_tool = GenerateImageTool()
    generate_prompt = "A simple monarch butterfly on a white background, cartoon style"
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))

    generated_result = await generate_tool.execute(
        context, 
        prompt=generate_prompt, 
        generation_config={},
        output_file_path="butterfly.png"
    )

    original_image_path = generated_result["file_path"]
    print(f"Generated image path for editing: {original_image_path}")
    # Step 2: Edit the generated image
    edit_tool = EditImageTool()
    edit_prompt = "Add a tiny party hat on the butterfly's head"

    edited_result = await edit_tool.execute(
        context, 
        prompt=edit_prompt, 
        input_images=original_image_path, 
        generation_config={},
        output_file_path="butterfly_hat.png"
    )

    edited_image_path = edited_result["file_path"]
    
    # Verify that a new image was created
    assert edited_image_path != original_image_path
    assert Path(edited_image_path).exists()


@pytest.mark.asyncio
async def test_edit_image_tool_with_remote_image(tmp_path):
    """
    Edits a remote reference image by overlaying text. Uses the public execute API.
    """
    edit_tool = EditImageTool()
    context = SimpleNamespace(agent_id="test-agent", workspace=_MockWorkspace(tmp_path))
    prompt = "Add the word 'Serenity' in white text across the center of the stone."
    remote_image_url = "http://192.168.2.124:29695/rest/files/images/smooth_stone_ref.jpg"

    result = await edit_tool.execute(
        context,
        prompt=prompt,
        input_images=remote_image_url,
        generation_config={},
        output_file_path="stone_text.png"
    )

    assert isinstance(result, dict)
    edited_path = result["file_path"]
    assert Path(edited_path).exists()
