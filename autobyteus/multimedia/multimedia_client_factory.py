import logging
from typing import Dict, Optional
from autobyteus.multimedia.autobyteus_provider import AutobyteusMultimediaModelProvider
from autobyteus.multimedia.base_multimedia_client import BaseMultimediaClient
from autobyteus.multimedia.models import MultimediaModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.api.openai_multimedia_client import OpenAIMultimediaClient
from autobyteus.multimedia.api.gemini_multimedia_client import GeminiMultimediaClient
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

class MultimediaClientFactory(metaclass=SingletonMeta):
    """
    A factory for creating instances of multimedia generation clients based on registered MultimediaModels.
    """
    _models_by_identifier: Dict[str, MultimediaModel] = {}
    _initialized = False

    @staticmethod
    def ensure_initialized():
        """Ensures the factory is initialized before use."""
        if not MultimediaClientFactory._initialized:
            MultimediaClientFactory._initialize_registry()
            MultimediaClientFactory._initialized = True

    @staticmethod
    def reinitialize():
        """Reinitializes the model registry, clearing all models and re-discovering them."""
        logger.info("Reinitializing Multimedia model registry...")
        MultimediaClientFactory._initialized = False
        MultimediaClientFactory._models_by_identifier.clear()
        MultimediaClientFactory.ensure_initialized()
        logger.info("Multimedia model registry reinitialized successfully.")

    @staticmethod
    def _initialize_registry():
        """Initializes the registry with built-in multimedia models and discovers remote ones."""
        
        # OpenAI Models
        gpt_image_1_model = MultimediaModel(
            name="gpt-image-1",
            value="dall-e-3",
            provider=MultimediaProvider.OPENAI,
            client_class=OpenAIMultimediaClient,
            parameter_schema={
                "n": {
                    "description": "The number of images to generate. Must be 1 for this model.",
                    "type": "integer",
                    "default": 1,
                    "allowed_values": [1]
                },
                "size": {
                    "description": "The size of the generated image.",
                    "type": "string",
                    "default": "1024x1024",
                    "allowed_values": ["1024x1024", "1792x1024", "1024x1792"]
                },
                "quality": {
                    "description": "The quality of the image. 'hd' creates images with finer details.",
                    "type": "string",
                    "default": "hd",
                    "allowed_values": ["standard", "hd"]
                },
                "style": {
                    "description": "The style of the generated images. Must be one of 'vivid' or 'natural'.",
                    "type": "string",
                    "default": "vivid",
                    "allowed_values": ["vivid", "natural"]
                }
            }
        )

        dall_e_2_model = MultimediaModel(
            name="dall-e-2",
            value="dall-e-2",
            provider=MultimediaProvider.OPENAI,
            client_class=OpenAIMultimediaClient,
            parameter_schema={
                "n": {
                    "description": "The number of images to generate.",
                    "type": "integer",
                    "default": 1,
                },
                "size": {
                    "description": "The size of the generated image.",
                    "type": "string",
                    "default": "1024x1024",
                    "allowed_values": ["256x256", "512x512", "1024x1024"]
                }
            }
        )

        # Google Imagen Models (via Gemini API)
        imagen_model = MultimediaModel(
            name="imagen-4",
            value="imagen-4.0-generate-001",
            provider=MultimediaProvider.GOOGLE,
            client_class=GeminiMultimediaClient,
            parameter_schema={} # The genai library doesn't expose these as simple params
        )

        models_to_register = [
            gpt_image_1_model,
            dall_e_2_model,
            imagen_model
        ]
        
        for model in models_to_register:
            MultimediaClientFactory.register_model(model)
        
        logger.info("Default API-based multimedia models registered.")

        # Discover models from remote Autobyteus servers
        AutobyteusMultimediaModelProvider.discover_and_register()


    @staticmethod
    def register_model(model: MultimediaModel):
        """
        Registers a new multimedia model.

        Args:
            model (MultimediaModel): The multimedia model instance to register.
        """
        identifier = model.model_identifier
        if identifier in MultimediaClientFactory._models_by_identifier:
            logger.warning(f"Multimedia model '{identifier}' is already registered. Overwriting.")
        
        # Ensure the provider enum is valid before registration
        if not isinstance(model.provider, MultimediaProvider):
            try:
                model.provider = MultimediaProvider(model.provider)
            except ValueError:
                logger.error(f"Cannot register model '{identifier}' with unknown provider '{model.provider}'.")
                return

        MultimediaClientFactory._models_by_identifier[identifier] = model

    @staticmethod
    def create_multimedia_client(model_identifier: str, config_override: Optional[MultimediaConfig] = None) -> BaseMultimediaClient:
        """
        Creates an instance of a registered multimedia client for a specific model.

        Args:
            model_identifier (str): The identifier of the model to use.
            config_override (Optional[MultimediaConfig]): Configuration to override the model's defaults.

        Returns:
            BaseMultimediaClient: An instance of the requested multimedia client.

        Raises:
            ValueError: If the requested model identifier is not registered.
        """
        MultimediaClientFactory.ensure_initialized()
        
        model = MultimediaClientFactory._models_by_identifier.get(model_identifier)
        if not model:
            raise ValueError(f"No multimedia model registered with the name '{model_identifier}'. "
                             f"Available models: {list(MultimediaClientFactory._models_by_identifier.keys())}")
        
        logger.info(f"Creating instance of multimedia client for model '{model_identifier}'.")
        return model.create_client(config_override)

# Create a default instance for easy access
multimedia_client_factory = MultimediaClientFactory()
