import pytest
import os
import re
from pathlib import Path
import logging

from autobyteus.tools.multimedia.audio_tools import GenerateSpeechTool, _get_configured_model_identifier
from autobyteus.tools.parameter_schema import ParameterType

logger = logging.getLogger(__name__)

TEST_TTS_MODEL = "gemini-2.5-flash-tts-rpa@localhost"

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set.")

@pytest.fixture
def set_default_speech_gen_model_env(monkeypatch):
    monkeypatch.setenv("DEFAULT_SPEECH_GENERATION_MODEL", TEST_TTS_MODEL)

def test_get_configured_model_identifier_success(set_default_speech_gen_model_env):
    """Tests that the helper function correctly reads the environment variable."""
    assert _get_configured_model_identifier("DEFAULT_SPEECH_GENERATION_MODEL", "fallback") == TEST_TTS_MODEL

def test_get_configured_model_identifier_fallback():
    """Tests that the helper function correctly uses the fallback."""
    assert _get_configured_model_identifier("NON_EXISTENT_VAR", "fallback_model") == "fallback_model"

def test_get_configured_model_identifier_failure():
    """Tests that a ValueError is raised if the environment variable is not set and no fallback is provided."""
    with pytest.raises(ValueError, match="environment variable is not set"):
        _get_configured_model_identifier("NON_EXISTENT_VAR")

def test_generate_speech_tool_dynamic_schema(set_default_speech_gen_model_env):
    """Tests that the speech tool's schema is generated dynamically and correctly."""
    tool = GenerateSpeechTool(config={})
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
    assert "voice_name" in properties
    assert properties["voice_name"]["type"] == "string"

@pytest.mark.asyncio
async def test_generate_speech_tool_execute(set_default_speech_gen_model_env):
    """Tests a successful execution of the GenerateSpeechTool."""
    tool = GenerateSpeechTool(config={})
    prompt = "This is a test of the speech generation tool."
    
    result = await tool._execute(context={}, prompt=prompt)
    
    assert isinstance(result, str)
    assert "Speech generation successful. Audio file(s) saved at:" in result
    
    # Cleanup the generated file
    match = re.search(r"\[\'(.*?)\'\]", result)
    if match:
        file_path_str = match.group(1)
        file_path = Path(file_path_str)
        if file_path.exists():
            os.remove(file_path)
    else:
        logger.warning(f"Could not parse file path from tool output to clean up: {result}")
