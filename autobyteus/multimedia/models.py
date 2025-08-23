from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Type, Optional, Iterator, Dict, Any
from urllib.parse import urlparse

from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

if TYPE_CHECKING:
    from autobyteus.multimedia.base_multimedia_client import BaseMultimediaClient

logger = logging.getLogger(__name__)

class MultimediaModelMeta(type):
    """
    Metaclass for MultimediaModel to allow discovery and access like an Enum.
    """
    def __iter__(cls) -> Iterator[MultimediaModel]:
        from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory
        MultimediaClientFactory.ensure_initialized()
        for model in MultimediaClientFactory._models_by_identifier.values():
            yield model

    def __getitem__(cls, name_or_identifier: str) -> MultimediaModel:
        from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory
        MultimediaClientFactory.ensure_initialized()
        model = MultimediaClientFactory._models_by_identifier.get(name_or_identifier)
        if model:
            return model
        raise KeyError(f"Multimedia model '{name_or_identifier}' not found.")

    def __len__(cls) -> int:
        from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory
        MultimediaClientFactory.ensure_initialized()
        return len(MultimediaClientFactory._models_by_identifier)


class MultimediaModel(metaclass=MultimediaModelMeta):
    """
    Represents a single multimedia model's metadata.
    """
    def __init__(
        self,
        name: str,
        value: str,
        provider: MultimediaProvider,
        client_class: Type["BaseMultimediaClient"],
        parameter_schema: Optional[Dict[str, Any]] = None,
        runtime: MultimediaRuntime = MultimediaRuntime.API,
        host_url: Optional[str] = None
    ):
        self.name = name
        self.value = value
        self.provider = provider
        self.client_class = client_class
        self.runtime = runtime
        self.host_url = host_url
        self.parameter_schema = parameter_schema if parameter_schema else {}

        # Automatically build default_config from the schema's default values
        default_params = {
            key: meta.get("default")
            for key, meta in self.parameter_schema.items()
            if "default" in meta
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

    def create_client(self, config_override: Optional[MultimediaConfig] = None) -> "BaseMultimediaClient":
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
            f"MultimediaModel(identifier='{self.model_identifier}', "
            f"provider='{self.provider.name}', runtime='{self.runtime.value}')"
        )
