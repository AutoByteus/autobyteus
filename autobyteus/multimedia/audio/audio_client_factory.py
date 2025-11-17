import logging
from typing import Dict, Optional

from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.audio.api.gemini_audio_client import GeminiAudioClient
from autobyteus.multimedia.audio.api.openai_audio_client import OpenAIAudioClient
from autobyteus.multimedia.audio.autobyteus_audio_provider import AutobyteusAudioModelProvider
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

# Enhanced metadata for Google Gemini TTS voices, including gender and description.
GEMINI_VOICE_DETAILS = {
    "Zephyr": {"gender": "female", "description": "Bright, Higher pitch"},
    "Puck": {"gender": "male", "description": "Upbeat, Middle pitch"},
    "Charon": {"gender": "male", "description": "Informative, Lower pitch"},
    "Kore": {"gender": "female", "description": "Firm, Middle pitch"},
    "Fenrir": {"gender": "male", "description": "Excitable, Lower middle pitch"},
    "Leda": {"gender": "female", "description": "Youthful, Higher pitch"},
    "Orus": {"gender": "male", "description": "Firm, Lower middle pitch"},
    "Aoede": {"gender": "female", "description": "Breezy, Middle pitch"},
    "Callirrhoe": {"gender": "female", "description": "Easy-going, Middle pitch"},
    "Autonoe": {"gender": "female", "description": "Bright, Middle pitch"},
    "Enceladus": {"gender": "male", "description": "Breathy, Lower pitch"},
    "Iapetus": {"gender": "male", "description": "Clear, Lower middle pitch"},
    "Umbriel": {"gender": "male", "description": "Easy-going, Lower middle pitch"},
    "Algieba": {"gender": "male", "description": "Smooth, Lower pitch"},
    "Despina": {"gender": "female", "description": "Smooth, Middle pitch"},
    "Erinome": {"gender": "female", "description": "Clear, Middle pitch"},
    "Algenib": {"gender": "male", "description": "Gravelly, Lower pitch"},
    "Rasalgethi": {"gender": "male", "description": "Informative, Middle pitch"},
    "Laomedeia": {"gender": "female", "description": "Upbeat, Higher pitch"},
    "Achernar": {"gender": "female", "description": "Soft, Higher pitch"},
    "Alnilam": {"gender": "male", "description": "Firm, Lower middle pitch"},
    "Schedar": {"gender": "male", "description": "Even, Lower middle pitch"},
    "Gacrux": {"gender": "female", "description": "Mature, Middle pitch"},
    "Pulcherrima": {"gender": "female", "description": "Forward, Middle pitch"},
    "Achird": {"gender": "male", "description": "Friendly, Lower middle pitch"},
    "Zubenelgenubi": {"gender": "male", "description": "Casual, Lower middle pitch"},
    "Vindemiatrix": {"gender": "female", "description": "Gentle, Middle pitch"},
    "Sadachbia": {"gender": "male", "description": "Lively, Lower pitch"},
    "Sadaltager": {"gender": "male", "description": "Knowledgeable, Middle pitch"},
    "Sulafat": {"gender": "female", "description": "Warm, Middle pitch"},
}

# The list of voice names, derived from the keys of the details dictionary.
# This is used for the `enum_values` to maintain compatibility.
GEMINI_TTS_VOICES = list(GEMINI_VOICE_DETAILS.keys())

# Generate a formatted string of voice metadata to be appended to parameter descriptions.
_voice_descriptions_list = [
    f"- {name} ({details['gender']}): {details['description']}"
    for name, details in GEMINI_VOICE_DETAILS.items()
]
GEMINI_VOICE_METADATA_DESC = "\n\nDetailed Voice Options:\n" + "\n".join(_voice_descriptions_list)


OPENAI_TTS_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable", "onyx",
    "nova", "sage", "shimmer", "verse"
]

class AudioClientFactory(metaclass=SingletonMeta):
    """
    A factory for creating instances of audio clients based on registered AudioModels.
    """
    _models_by_identifier: Dict[str, AudioModel] = {}
    _initialized = False

    @staticmethod
    def ensure_initialized():
        """Ensures the factory is initialized before use."""
        if not AudioClientFactory._initialized:
            AudioClientFactory._initialize_registry()
            AudioClientFactory._initialized = True

    @staticmethod
    def reinitialize():
        """Reinitializes the model registry, clearing all models and re-discovering them."""
        logger.info("Reinitializing Audio model registry...")
        AudioClientFactory._initialized = False
        AudioClientFactory._models_by_identifier.clear()
        AudioClientFactory.ensure_initialized()
        logger.info("Audio model registry reinitialized successfully.")

    @staticmethod
    def _initialize_registry():
        """Initializes the registry with built-in audio models."""
        
        # --- Define a clear schema for speaker mapping items using ParameterSchema ---
        speaker_mapping_item_schema = ParameterSchema(parameters=[
            ParameterDefinition(
                name="speaker",
                param_type=ParameterType.STRING,
                description="The speaker's name as it appears in the prompt (e.g., 'Joe').",
                required=True
            ),
            ParameterDefinition(
                name="voice",
                param_type=ParameterType.ENUM,
                description="The voice to assign to this speaker." + GEMINI_VOICE_METADATA_DESC,
                enum_values=GEMINI_TTS_VOICES,
                required=True
            )
        ])

        # Google Gemini Audio Models
        gemini_tts_schema = ParameterSchema(parameters=[
            ParameterDefinition(
                name="mode",
                param_type=ParameterType.ENUM,
                default_value="single-speaker",
                enum_values=["single-speaker", "multi-speaker"],
                description="The speech generation mode. 'single-speaker' for a consistent voice, or 'multi-speaker' to assign different voices to speakers identified in the prompt."
            ),
            ParameterDefinition(
                name="voice_name",
                param_type=ParameterType.ENUM,
                default_value="Kore",
                enum_values=GEMINI_TTS_VOICES,
                description="The voice to use for single-speaker generation." + GEMINI_VOICE_METADATA_DESC
            ),
            ParameterDefinition(
                name="style_instructions",
                param_type=ParameterType.STRING,
                description="Optional instructions on the style of speech, e.g., 'Say this in a dramatic whisper'."
            ),
            ParameterDefinition(
                name="speaker_mapping",
                param_type=ParameterType.ARRAY,
                description="Required for multi-speaker mode. A list of objects, each mapping a speaker name from the prompt to a voice name.",
                array_item_schema=speaker_mapping_item_schema
            )
        ])
        
        gemini_tts_model = AudioModel(
            name="gemini-2.5-flash-tts",
            value="gemini-2.5-flash-preview-tts",
            provider=MultimediaProvider.GOOGLE,
            client_class=GeminiAudioClient,
            parameter_schema=gemini_tts_schema
        )

        openai_tts_schema = ParameterSchema(parameters=[
            ParameterDefinition(
                name="voice",
                param_type=ParameterType.ENUM,
                default_value="alloy",
                enum_values=OPENAI_TTS_VOICES,
                description="The OpenAI TTS voice to use for generation."
            ),
            ParameterDefinition(
                name="format",
                param_type=ParameterType.ENUM,
                default_value="mp3",
                enum_values=["mp3", "wav"],
                description="The audio format to generate."
            ),
            ParameterDefinition(
                name="instructions",
                param_type=ParameterType.STRING,
                description="Optional delivery instructions (tone, pacing, accent, etc.)."
            )
        ])

        openai_tts_model = AudioModel(
            name="gpt-4o-mini-tts",
            value="gpt-4o-mini-tts",
            provider=MultimediaProvider.OPENAI,
            client_class=OpenAIAudioClient,
            parameter_schema=openai_tts_schema
        )

        models_to_register = [
            openai_tts_model,
            gemini_tts_model,
        ]
        
        for model in models_to_register:
            AudioClientFactory.register_model(model)
        
        logger.info("Default API-based audio models registered.")
        
        # Discover models from remote Autobyteus servers
        AutobyteusAudioModelProvider.discover_and_register()

    @staticmethod
    def register_model(model: AudioModel):
        """Registers a new audio model."""
        identifier = model.model_identifier
        if identifier in AudioClientFactory._models_by_identifier:
            logger.warning(f"Audio model '{identifier}' is already registered. Overwriting.")
        
        if not isinstance(model.provider, MultimediaProvider):
            try:
                model.provider = MultimediaProvider(model.provider)
            except ValueError:
                logger.error(f"Cannot register model '{identifier}' with unknown provider '{model.provider}'.")
                return

        AudioClientFactory._models_by_identifier[identifier] = model

    @staticmethod
    def create_audio_client(model_identifier: str, config_override: Optional[MultimediaConfig] = None) -> BaseAudioClient:
        """Creates an instance of a registered audio client for a specific model."""
        AudioClientFactory.ensure_initialized()
        
        model = AudioClientFactory._models_by_identifier.get(model_identifier)
        if not model:
            raise ValueError(f"No audio model registered with the name '{model_identifier}'. "
                             f"Available models: {list(AudioClientFactory._models_by_identifier.keys())}")
        
        logger.info(f"Creating instance of audio client for model '{model_identifier}'.")
        return model.create_client(config_override)

audio_client_factory = AudioClientFactory()
