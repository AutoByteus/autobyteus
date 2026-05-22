from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Type, Optional, Iterator, Dict, Any, Union
from urllib.parse import urlparse

from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig
from autobyteus.utils.parameter_schema import ParameterSchema

if TYPE_CHECKING:
    from autobyteus.multimedia.video.base_video_client import BaseVideoClient

logger = logging.getLogger(__name__)


class VideoModelMeta(type):
    """
    Metaclass for VideoModel to allow discovery and access like an Enum.
    """
    def __iter__(cls) -> Iterator[VideoModel]:
        from autobyteus.multimedia.video.video_client_factory import VideoClientFactory
        VideoClientFactory.ensure_initialized()
        for model in VideoClientFactory._models_by_identifier.values():
            yield model

    def __getitem__(cls, name_or_identifier: str) -> VideoModel:
        from autobyteus.multimedia.video.video_client_factory import VideoClientFactory
        return VideoClientFactory.get_model(name_or_identifier)

    def __len__(cls) -> int:
        from autobyteus.multimedia.video.video_client_factory import VideoClientFactory
        VideoClientFactory.ensure_initialized()
        return len(VideoClientFactory._models_by_identifier)


class VideoModel(metaclass=VideoModelMeta):
    """
    Represents a single video model's metadata.
    """
    def __init__(
        self,
        name: str,
        value: str,
        provider: MultimediaProvider,
        client_class: Type["BaseVideoClient"],
        parameter_schema: Optional[Union[Dict[str, Any], ParameterSchema]] = None,
        runtime: MultimediaRuntime = MultimediaRuntime.API,
        host_url: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.name = name
        self.value = value
        self.provider = provider
        self.client_class = client_class
        self.runtime = runtime
        self.host_url = host_url
        self.description = description

        if isinstance(parameter_schema, dict):
            self.parameter_schema = ParameterSchema.from_dict(parameter_schema)
        elif parameter_schema is None:
            self.parameter_schema = ParameterSchema()
        else:
            self.parameter_schema = parameter_schema

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
                parsed = urlparse(self.host_url)
                host = parsed.netloc or parsed.hostname or self.host_url
                return f"{self.name}@{host}"
            except Exception:
                return f"{self.name}@{self.host_url}"
        return self.name

    def create_client(self, config_override: Optional[MultimediaConfig] = None) -> "BaseVideoClient":
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
            f"VideoModel(identifier='{self.model_identifier}', "
            f"provider='{self.provider.name}', runtime='{self.runtime.value}')"
        )
