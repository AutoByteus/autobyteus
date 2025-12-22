import pytest
import os
from pathlib import Path
import logging
from types import SimpleNamespace

from autobyteus.tools.multimedia.audio_tools import GenerateSpeechTool, _get_configured_model_identifier
from autobyteus.utils.parameter_schema import ParameterType, ParameterSchema, ParameterDefinition

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set, skipping audio tool integration tests.")

@pytest.fixture(autouse=True)
def fix_models(monkeypatch):
    """Force valid model names for integration tests."""
    monkeypatch.setenv("DEFAULT_SPEECH_GENERATION_MODEL", "gemini-2.5-flash-tts")

def test_get_configured_model_identifier_success(monkeypatch):
    """Tests that the helper function correctly reads the environment variable."""
    monkeypatch.setenv("DEFAULT_SPEECH_GENERATION_MODEL", "test-model")
    assert _get_configured_model_identifier("DEFAULT_SPEECH_GENERATION_MODEL", "fallback") == "test-model"

def test_get_configured_model_identifier_fallback():
    """Tests that the helper function correctly uses the fallback."""
    assert _get_configured_model_identifier("NON_EXISTENT_VAR_FOR_TEST", "fallback_model") == "fallback_model"

def test_get_configured_model_identifier_failure():
    """Tests that a ValueError is raised if the environment variable is not set and no fallback is provided."""
    with pytest.raises(ValueError, match="environment variable is not set"):
        _get_configured_model_identifier("NON_EXISTENT_VAR_FOR_TEST_FAIL")

def test_generate_speech_tool_dynamic_schema():
    """
    Tests that the speech tool's schema is generated dynamically and correctly,
    including validation for the complex 'speaker_mapping' parameter.
    """
    tool = GenerateSpeechTool()
    schema = tool.get_argument_schema()
    
    assert isinstance(schema, ParameterSchema)
    params_dict = {p.name: p for p in schema.parameters}
    
    # Check for base parameters
    assert "prompt" in params_dict
    assert params_dict["prompt"].param_type == ParameterType.STRING
    
    # Check for the generation_config object
    assert "generation_config" in params_dict
    config_param = params_dict["generation_config"]
    assert config_param.param_type == ParameterType.OBJECT
    
    # Inspect the nested schema for generation_config
    object_schema = config_param.object_schema
    assert isinstance(object_schema, ParameterSchema)
    
    config_params_dict = {p.name: p for p in object_schema.parameters}
    assert "voice_name" in config_params_dict
    assert "mode" in config_params_dict
    assert "speaker_mapping" in config_params_dict

    # Deeply inspect the 'speaker_mapping' parameter
    speaker_mapping_param = config_params_dict["speaker_mapping"]
    assert speaker_mapping_param.param_type == ParameterType.ARRAY
    
    # The item schema should now be a ParameterSchema object
    item_schema = speaker_mapping_param.array_item_schema
    assert isinstance(item_schema, ParameterSchema)

    # Inspect the parameters of the nested schema
    speaker_param = item_schema.get_parameter("speaker")
    assert isinstance(speaker_param, ParameterDefinition)
    assert speaker_param.param_type == ParameterType.STRING
    assert speaker_param.required is True

    voice_param = item_schema.get_parameter("voice")
    assert isinstance(voice_param, ParameterDefinition)
    assert voice_param.param_type == ParameterType.ENUM
    assert voice_param.required is True
    assert isinstance(voice_param.enum_values, list)


@pytest.mark.asyncio
async def test_generate_speech_tool_execute_single_speaker(tmp_path):
    """Tests a successful single-speaker execution of the GenerateSpeechTool."""
    tool = GenerateSpeechTool()
    prompt = "This is a test of the single-speaker speech generation tool."
    context = SimpleNamespace(agent_id="test-agent", workspace_root=tmp_path)

    result_path = None
    try:
        result = await tool.execute(context, prompt=prompt, output_file_path="single_speaker.wav")

        assert isinstance(result, dict)
        assert "file_path" in result
        file_path_str = result["file_path"]
        assert file_path_str.endswith(".wav")

        file_path = Path(file_path_str)
        assert file_path.exists()
        assert file_path.stat().st_size > 50  # Check that file is not empty
        result_path = file_path_str
        
    finally:
        # Cleanup the generated file(s)
        if result_path:
            try:
                if os.path.exists(result_path):
                    os.remove(result_path)
            except Exception as e:
                logger.warning(f"Could not clean up test file {result_path}: {e}")

@pytest.mark.asyncio
async def test_generate_speech_tool_execute_multi_speaker(tmp_path):
    """Tests a successful multi-speaker execution of the GenerateSpeechTool."""
    tool = GenerateSpeechTool()
    prompt = "Joe: Hello, this is Joe.\n" \
             "Jane: And this is Jane, testing the multi-speaker functionality."
    generation_config = {
        "mode": "multi-speaker",
        "speaker_mapping": [
            {"speaker": "Joe", "voice": "Puck"},
            {"speaker": "Jane", "voice": "Kore"}
        ],
        "style_instructions": "Speak in a clear, conversational tone."
    }
    
    context = SimpleNamespace(agent_id="test-agent", workspace_root=tmp_path)
    result_path = None
    try:
        result = await tool.execute(
            context,
            prompt=prompt, 
            generation_config=generation_config,
            output_file_path="multi_speaker.wav"
        )

        assert isinstance(result, dict)
        assert "file_path" in result
        file_path_str = result["file_path"]
        assert file_path_str.endswith(".wav")

        file_path = Path(file_path_str)
        assert file_path.exists()
        assert file_path.stat().st_size > 50  # Check that file is not empty
        result_path = file_path_str
        
    finally:
        # Cleanup the generated file(s)
        if result_path:
            try:
                if os.path.exists(result_path):
                    os.remove(result_path)
            except Exception as e:
                logger.warning(f"Could not clean up test file {result_path}: {e}")