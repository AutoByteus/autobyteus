import pytest
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

# --- Fixtures ---

class DummyAudioClient(BaseAudioClient):
    """A dummy client class for testing purposes."""
    async def generate_speech(self, prompt, generation_config=None, **kwargs):
        pass

@pytest.fixture
def sample_schema_dict():
    """Provides a sample parameter schema as a dictionary."""
    return {
        "parameters": [
            {
                "name": "voice_name",
                "type": "enum",
                "description": "The voice to use.",
                "required": False,
                "default_value": "Kore",
                "enum_values": ["Kore", "Zephyr"]
            },
            {
                "name": "speed",
                "type": "float",
                "description": "The speech speed.",
                "required": True,
                "default_value": None,
                "min_value": 0.5,
                "max_value": 2.0
            }
        ]
    }

@pytest.fixture
def sample_schema_object():
    """Provides a sample parameter schema as a ParameterSchema object."""
    return ParameterSchema(parameters=[
        ParameterDefinition(
            name="voice_name",
            param_type=ParameterType.ENUM,
            description="The voice to use.",
            default_value="Kore",
            enum_values=["Kore", "Zephyr"]
        ),
        ParameterDefinition(
            name="speed",
            param_type=ParameterType.FLOAT,
            description="The speech speed.",
            required=True
        )
    ])

# --- Test Cases ---

def test_init_with_dict_schema(sample_schema_dict):
    """
    Tests that the AudioModel constructor correctly deserializes a dictionary
    into a ParameterSchema object.
    """
    model = AudioModel(
        name="test-model",
        value="test-model-v1",
        provider=MultimediaProvider.GOOGLE,
        client_class=DummyAudioClient,
        parameter_schema=sample_schema_dict
    )
    
    assert isinstance(model.parameter_schema, ParameterSchema)
    assert len(model.parameter_schema.parameters) == 2
    
    voice_param = model.parameter_schema.get_parameter("voice_name")
    assert voice_param is not None
    assert voice_param.param_type == ParameterType.ENUM
    assert voice_param.default_value == "Kore"

def test_init_with_parameter_schema_object(sample_schema_object):
    """
    Tests that the AudioModel constructor correctly accepts a ParameterSchema object directly.
    """
    model = AudioModel(
        name="test-model",
        value="test-model-v1",
        provider=MultimediaProvider.GOOGLE,
        client_class=DummyAudioClient,
        parameter_schema=sample_schema_object
    )

    assert model.parameter_schema is sample_schema_object
    assert len(model.parameter_schema.parameters) == 2

def test_init_with_none_schema():
    """
    Tests that the AudioModel constructor creates an empty ParameterSchema when None is provided.
    """
    model = AudioModel(
        name="test-model",
        value="test-model-v1",
        provider=MultimediaProvider.GOOGLE,
        client_class=DummyAudioClient,
        parameter_schema=None
    )
    
    assert isinstance(model.parameter_schema, ParameterSchema)
    assert len(model.parameter_schema.parameters) == 0

def test_init_populates_default_config(sample_schema_dict):
    """
    Tests that the default_config is correctly populated from the default values
    in the provided parameter schema.
    """
    model = AudioModel(
        name="test-model",
        value="test-model-v1",
        provider=MultimediaProvider.GOOGLE,
        client_class=DummyAudioClient,
        parameter_schema=sample_schema_dict
    )
    
    assert isinstance(model.default_config, MultimediaConfig)
    
    expected_defaults = {"voice_name": "Kore"}
    assert model.default_config.to_dict() == expected_defaults

def test_init_populates_empty_default_config():
    """
    Tests that the default_config is empty when the schema has no default values.
    """
    schema = {
        "parameters": [{
            "name": "speed", "type": "float", "description": "speed", "required": True
        }]
    }
    model = AudioModel(
        name="test-model",
        value="test-model-v1",
        provider=MultimediaProvider.GOOGLE,
        client_class=DummyAudioClient,
        parameter_schema=schema
    )
    
    assert isinstance(model.default_config, MultimediaConfig)
    assert model.default_config.to_dict() == {}
