import logging
from typing import Dict, Optional
from autobyteus.multimedia.image.autobyteus_image_provider import AutobyteusImageModelProvider
from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.image.image_model import ImageModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.image.api.openai_image_client import OpenAIImageClient
from autobyteus.multimedia.image.api.gemini_image_client import GeminiImageClient
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.singleton import SingletonMeta
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

logger = logging.getLogger(__name__)

class ImageClientFactory(metaclass=SingletonMeta):
    """
    A factory for creating instances of image generation clients based on registered ImageModels.
    """
    _models_by_identifier: Dict[str, ImageModel] = {}
    _initialized = False

    @staticmethod
    def ensure_initialized():
        """Ensures the factory is initialized before use."""
        if not ImageClientFactory._initialized:
            ImageClientFactory._initialize_registry()
            ImageClientFactory._initialized = True

    @staticmethod
    def reinitialize():
        """Reinitializes the model registry, clearing all models and re-discovering them."""
        logger.info("Reinitializing Image model registry...")
        ImageClientFactory._initialized = False
        ImageClientFactory._models_by_identifier.clear()
        ImageClientFactory.ensure_initialized()
        logger.info("Image model registry reinitialized successfully.")

    @staticmethod
    def _initialize_registry():
        """Initializes the registry with built-in image models and discovers remote ones."""
        
        # OpenAI Models
        gpt_image_15_schema = ParameterSchema(parameters=[
            ParameterDefinition(name="n", param_type=ParameterType.INTEGER, default_value=1, enum_values=[1], description="The number of images to generate."),
            ParameterDefinition(name="size", param_type=ParameterType.ENUM, default_value="1024x1024", enum_values=["1024x1024", "1792x1024", "1024x1792"], description="The size of the generated images."),
            ParameterDefinition(name="quality", param_type=ParameterType.ENUM, default_value="auto", enum_values=["auto", "low", "medium", "high"], description="The quality of the image that will be generated.")
        ])

        gemini_image_schema = ParameterSchema(parameters=[
            ParameterDefinition(name="n", param_type=ParameterType.INTEGER, default_value=1, enum_values=[1], description="The number of images to generate."),
            ParameterDefinition(name="size", param_type=ParameterType.ENUM, default_value="1024x1024", enum_values=["1024x1024", "1792x1024", "1024x1792"], description="The size of the generated images."),
            ParameterDefinition(name="quality", param_type=ParameterType.ENUM, default_value="auto", enum_values=["auto", "low", "medium", "high"], description="The quality of the image that will be generated.")
        ])

        gpt_image_15_model = ImageModel(
            name="gpt-image-1.5",
            value="gpt-image-1.5",
            provider=MultimediaProvider.OPENAI,
            client_class=OpenAIImageClient,
            parameter_schema=gpt_image_15_schema,
            description=(
                "OpenAI's latest **stateless (single-turn)** image model with faster renders, improved text rendering, "
                "and higher fidelity edits. Same API surface as gpt-image-1."
            )
        )

        # Google Imagen Models (via Gemini API)
        imagen_model = ImageModel(
            name="imagen-4",
            value="imagen-4.0-generate-001",
            provider=MultimediaProvider.GEMINI,
            client_class=GeminiImageClient,
            parameter_schema=None, # The genai library doesn't expose these as simple params
            description=(
                "A high-fidelity **stateless (single-turn)** model. "
                "Does **NOT** support input images (text-to-image only). "
                "Any provided input images will be ignored."
            )
        )

        # Google Gemini 2.5 Flash Image (legacy, still widely available)
        gemini_flash_image_model = ImageModel(
            name="gemini-2.5-flash-image",
            value="gemini-2.5-flash-image",
            provider=MultimediaProvider.GEMINI,
            client_class=GeminiImageClient,
            parameter_schema=None,  # Parameters handled by genai library
            description=(
                "Fast **conversational (multi-turn)** multimodal image model. "
                "Supports context retention and input images for edits/variations."
            )
        )

        # Google Gemini 3 Pro Image (aka "Nano Banana Pro")
        gemini_pro_image_model = ImageModel(
            name="gemini-3-pro-image-preview",
            value="gemini-3-pro-image-preview",
            provider=MultimediaProvider.GEMINI,
            client_class=GeminiImageClient,
            parameter_schema=None,  # genai library handles options internally
            description=(
                "High-quality **conversational (multi-turn)** image model for complex edits and 4K renders. "
                "Supports up to 14 reference images, advanced text rendering, and thinking mode."
            )
        )

        models_to_register = [
            gpt_image_15_model,
            imagen_model,
            gemini_flash_image_model,
            gemini_pro_image_model,
        ]
        
        for model in models_to_register:
            ImageClientFactory.register_model(model)
        
        logger.info("Default API-based image models registered.")

        # Discover models from remote Autobyteus servers
        AutobyteusImageModelProvider.discover_and_register()

    @staticmethod
    def register_model(model: ImageModel):
        """Registers a new image model."""
        identifier = model.model_identifier
        if identifier in ImageClientFactory._models_by_identifier:
            logger.warning(f"Image model '{identifier}' is already registered. Overwriting.")
        
        if not isinstance(model.provider, MultimediaProvider):
            try:
                model.provider = MultimediaProvider(model.provider)
            except ValueError:
                logger.error(f"Cannot register model '{identifier}' with unknown provider '{model.provider}'.")
                return

        ImageClientFactory._models_by_identifier[identifier] = model

    @staticmethod
    def create_image_client(model_identifier: str, config_override: Optional[MultimediaConfig] = None) -> BaseImageClient:
        """Creates an instance of a registered image client for a specific model."""
        ImageClientFactory.ensure_initialized()
        
        model = ImageClientFactory._models_by_identifier.get(model_identifier)
        if not model:
            raise ValueError(f"No image model registered with the name '{model_identifier}'. "
                             f"Available models: {list(ImageClientFactory._models_by_identifier.keys())}")
        
        logger.info(f"Creating instance of image client for model '{model_identifier}'.")
        return model.create_client(config_override)

image_client_factory = ImageClientFactory()
