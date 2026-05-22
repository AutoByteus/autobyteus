import logging
from typing import Dict, Optional

from autobyteus.clients.autobyteus_client import AutobyteusClient
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.multimedia.video.api.autobyteus_video_client import AutobyteusVideoClient
from autobyteus.multimedia.video.autobyteus_video_provider import AutobyteusVideoModelProvider
from autobyteus.multimedia.video.base_video_client import BaseVideoClient
from autobyteus.multimedia.video.video_model import VideoModel
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_MODEL_NAME = "gemini-omni-app-rpa"
DEFAULT_VIDEO_MODEL_VALUE = "gemini-omni-app"


class VideoClientFactory(metaclass=SingletonMeta):
    """
    A factory for creating instances of video generation clients based on registered VideoModels.
    """
    _models_by_identifier: Dict[str, VideoModel] = {}
    _initialized = False

    @staticmethod
    def ensure_initialized():
        """Ensures the factory is initialized before use."""
        if not VideoClientFactory._initialized:
            VideoClientFactory._initialize_registry()
            VideoClientFactory._initialized = True

    @staticmethod
    def reinitialize():
        """Reinitializes the model registry, clearing all models and re-discovering them."""
        logger.info("Reinitializing Video model registry...")
        VideoClientFactory._initialized = False
        VideoClientFactory._models_by_identifier.clear()
        VideoClientFactory.ensure_initialized()
        logger.info("Video model registry reinitialized successfully.")

    @staticmethod
    def _initialize_registry():
        """Initializes the registry with the default Autobyteus video model and discovers remote ones."""
        default_model = VideoModel(
            name=DEFAULT_VIDEO_MODEL_NAME,
            value=DEFAULT_VIDEO_MODEL_VALUE,
            provider=MultimediaProvider.AUTOBYTEUS,
            client_class=AutobyteusVideoClient,
            parameter_schema=None,
            runtime=MultimediaRuntime.AUTOBYTEUS,
            host_url=AutobyteusClient.get_default_server_url(),
            description=(
                "Gemini App video generation through the Autobyteus RPA LLM server. "
                "Supports a text prompt and optional image, audio, or video inputs."
            ),
        )
        VideoClientFactory.register_model(default_model)
        logger.info("Default Autobyteus video model registered.")

        AutobyteusVideoModelProvider.discover_and_register()

    @staticmethod
    def register_model(model: VideoModel):
        """Registers a new video model."""
        identifier = model.model_identifier
        if identifier in VideoClientFactory._models_by_identifier:
            logger.warning("Video model '%s' is already registered. Overwriting.", identifier)

        if not isinstance(model.provider, MultimediaProvider):
            try:
                model.provider = MultimediaProvider(model.provider)
            except ValueError:
                logger.error("Cannot register model '%s' with unknown provider '%s'.", identifier, model.provider)
                return

        VideoClientFactory._models_by_identifier[identifier] = model

    @staticmethod
    def get_model(model_identifier: str) -> VideoModel:
        """Returns a registered video model by exact identifier or unique unqualified model name."""
        VideoClientFactory.ensure_initialized()

        model = VideoClientFactory._models_by_identifier.get(model_identifier)
        if model:
            return model

        name_matches = [
            candidate for candidate in VideoClientFactory._models_by_identifier.values()
            if candidate.name == model_identifier
        ]
        if len(name_matches) == 1:
            return name_matches[0]

        available_models = list(VideoClientFactory._models_by_identifier.keys())
        if len(name_matches) > 1:
            raise ValueError(
                f"Ambiguous video model '{model_identifier}'. "
                f"Use one of the host-qualified identifiers: {available_models}"
            )

        raise ValueError(
            f"No video model registered with the name '{model_identifier}'. "
            f"Available models: {available_models}"
        )

    @staticmethod
    def create_video_client(
        model_identifier: str,
        config_override: Optional[MultimediaConfig] = None
    ) -> BaseVideoClient:
        """Creates an instance of a registered video client for a specific model."""
        model = VideoClientFactory.get_model(model_identifier)

        logger.info("Creating instance of video client for model '%s'.", model.model_identifier)
        return model.create_client(config_override)


video_client_factory = VideoClientFactory()
