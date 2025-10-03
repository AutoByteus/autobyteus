import pytest
import os
from pathlib import Path
import logging

from autobyteus.tools.multimedia.audio_tools import GenerateSpeechTool, _get_configured_model_identifier
from autobyteus.utils.parameter_schema import ParameterType, ParameterSchema

logger = logging.getLogger(__name__)

@pytest.fixture(scope="module", autouse=True)
def check_api_keys():
    if not os.getenv("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set, skipping audio tool integration tests.")

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
    
    # The item schema can be a dict or a ParameterSchema object
    item_schema_repr = speaker_mapping_param.array_item_schema
    assert item_schema_repr is not None

    # We expect it to be a dict representing a JSON schema
    assert isinstance(item_schema_repr, dict)
    assert item_schema_repr.get("type") == "object"
    
    properties = item_schema_repr.get("properties", {})
    assert "speaker" in properties
    assert "voice" in properties
    assert properties["speaker"]["type"] == "string"
    assert properties["voice"]["type"] == "string" # It's an enum, which maps to string in JSON schema
    assert "enum" in properties["voice"]
    
    required = item_schema_repr.get("required", [])
    assert "speaker" in required
    assert "voice" in required


@pytest.mark.asyncio
async def test_generate_speech_tool_execute_single_speaker():
    """Tests a successful single-speaker execution of the GenerateSpeechTool."""
    tool = GenerateSpeechTool()
    prompt = "This is a test of the single-speaker speech generation tool."
    
    result_paths = []
    try:
        result_paths = await tool._execute(context={}, prompt=prompt)
        
        assert isinstance(result_paths, list)
        assert len(result_paths) > 0
        
        file_path_str = result_paths[0]
        assert isinstance(file_path_str, str)
        assert file_path_str.endswith(".wav")
        
        file_path = Path(file_path_str)
        assert file_path.exists()
        assert file_path.stat().st_size > 1000  # Check that file is not empty
        
    finally:
        # Cleanup the generated file(s)
        for path_str in result_paths:
            try:
                if os.path.exists(path_str):
                    os.remove(path_str)
            except Exception as e:
                logger.warning(f"Could not clean up test file {path_str}: {e}")

@pytest.mark.asyncio
async def test_generate_speech_tool_execute_multi_speaker():
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
    
    result_paths = []
    try:
        result_paths = await tool._execute(
            context={}, 
            prompt=prompt, 
            generation_config=generation_config
        )
        
        assert isinstance(result_paths, list)
        assert len(result_paths) > 0
        
        file_path_str = result_paths[0]
        assert isinstance(file_path_str, str)
        assert file_path_str.endswith(".wav")
        
        file_path = Path(file_path_str)
        assert file_path.exists()
        assert file_path.stat().st_size > 1000  # Check that file is not empty
        
    finally:
        # Cleanup the generated file(s)
        for path_str in result_paths:
            try:
                if os.path.exists(path_str):
                    os.remove(path_str)
            except Exception as e:
                logger.warning(f"Could not clean up test file {path_str}: {e}")
