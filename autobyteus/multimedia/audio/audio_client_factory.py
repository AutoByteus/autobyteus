import logging
from typing import Dict, Optional

from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.audio.api.gemini_audio_client import GeminiAudioClient
from autobyteus.multimedia.audio.autobyteus_audio_provider import AutobyteusAudioModelProvider
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

GEMINI_TTS_VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", 
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", 
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar", 
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", 
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"
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
                description="The voice to assign to this speaker.",
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
                description="The voice to use for single-speaker generation."
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

        models_to_register = [
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
