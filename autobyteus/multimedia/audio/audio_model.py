from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Type, Optional, Iterator, Dict, Any, Union
from urllib.parse import urlparse

from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.parameter_schema import ParameterSchema

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient

logger = logging.getLogger(__name__)

class AudioModelMeta(type):
    """
    Metaclass for AudioModel to allow discovery and access like an Enum.
    """
    def __iter__(cls) -> Iterator[AudioModel]:
        from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory
        AudioClientFactory.ensure_initialized()
        for model in AudioClientFactory._models_by_identifier.values():
            yield model

    def __getitem__(cls, name_or_identifier: str) -> AudioModel:
        from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory
        AudioClientFactory.ensure_initialized()
        model = AudioClientFactory._models_by_identifier.get(name_or_identifier)
        if model:
            return model
        available_models = list(AudioClientFactory._models_by_identifier.keys())
        raise KeyError(f"Audio model '{name_or_identifier}' not found. Available models: {available_models}")

    def __len__(cls) -> int:
        from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory
        AudioClientFactory.ensure_initialized()
        return len(AudioClientFactory._models_by_identifier)


class AudioModel(metaclass=AudioModelMeta):
    """
    Represents a single audio model's metadata.
    """
    def __init__(
        self,
        name: str,
        value: str,
        provider: MultimediaProvider,
        client_class: Type["BaseAudioClient"],
        parameter_schema: Optional[Union[Dict[str, Any], ParameterSchema]] = None,
        runtime: MultimediaRuntime = MultimediaRuntime.API,
        host_url: Optional[str] = None
    ):
        self.name = name
        self.value = value
        self.provider = provider
        self.client_class = client_class
        self.runtime = runtime
        self.host_url = host_url

        if isinstance(parameter_schema, dict):
            self.parameter_schema = ParameterSchema.from_dict(parameter_schema)
        elif parameter_schema is None:
            self.parameter_schema = ParameterSchema()
        else:
            self.parameter_schema = parameter_schema

        # Automatically build default_config from the schema's default values
        default_params = {
            param.name: param.default_value
            for param in self.parameter_schema.parameters
            if param.default_value is not None
        }
        self.default_config = MultimediaConfig(params=default_params)

    @property
    def model_identifier(self) -> str:
        """Returns the unique identifier for the model."""
        if self.runtime == MultimediaRuntime.AUTOBYTEUS and self.host_url:
            try:
                host = urlparse(self.host_url).hostname
                return f"{self.name}@{host}"
            except Exception:
                return f"{self.name}@{self.host_url}" # Fallback
        return self.name

    def create_client(self, config_override: Optional[MultimediaConfig] = None) -> "BaseAudioClient":
        """
        Instantiates the client class for this model.
        """
        config_to_use = self.default_config
        if config_override:
            from copy import deepcopy
            config_to_use = deepcopy(self.default_config)
            config_to_use.merge_with(config_override)
        
        return self.client_class(model=self, config=config_to_use)

    def __repr__(self):
        return (
            f"AudioModel(identifier='{self.model_identifier}', "
            f"provider='{self.provider.name}', runtime='{self.runtime.value}')"
        )
