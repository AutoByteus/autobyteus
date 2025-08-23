import logging
from typing import Dict, Any, List
import os
from urllib.parse import urlparse

from autobyteus_llm_client import AutobyteusClient
from autobyteus.multimedia.api.autobyteus_multimedia_client import AutobyteusMultimediaClient
from autobyteus.multimedia.models import MultimediaModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class AutobyteusMultimediaModelProvider:
    """
    Discovers and registers multimedia models from remote Autobyteus server instances.
    """
    DEFAULT_SERVER_URL = 'http://localhost:8000'

    @staticmethod
    def _get_hosts() -> List[str]:
        """Gets Autobyteus server hosts from env vars."""
        hosts_str = os.getenv('AUTOBYTEUS_LLM_SERVER_HOSTS')
        if hosts_str:
            return [host.strip() for host in hosts_str.split(',')]
        
        legacy_host = os.getenv('AUTOBYTEUS_LLM_SERVER_URL')
        if legacy_host:
            return [legacy_host]
            
        return [AutobyteusMultimediaModelProvider.DEFAULT_SERVER_URL]

    @staticmethod
    def discover_and_register():
        """Discover and register multimedia models from all configured hosts."""
        try:
            from autobyteus.multimedia.multimedia_client_factory import MultimediaClientFactory

            hosts = AutobyteusMultimediaModelProvider._get_hosts()
            total_registered_count = 0

            for host_url in hosts:
                if not AutobyteusMultimediaModelProvider.is_valid_url(host_url):
                    logger.error(f"Invalid Autobyteus host URL for multimedia discovery: {host_url}, skipping.")
                    continue
                
                logger.info(f"Discovering multimedia models from host: {host_url}")
                client = None
                try:
                    client = AutobyteusClient(server_url=host_url)
                    response = client.get_available_multimedia_models_sync()
                except Exception as e:
                    logger.warning(f"Could not fetch multimedia models from Autobyteus server at {host_url}: {e}")
                    continue
                finally:
                    if client:
                        client.sync_client.close()

                if not response.get('models'):
                    logger.info(f"No multimedia models found on host {host_url}.")
                    continue

                models = response.get('models', [])
                host_registered_count = 0
                for model_info in models:
                    try:
                        # Basic validation
                        if not all(k in model_info for k in ["name", "value", "provider"]):
                            logger.warning(f"Skipping malformed multimedia model from {host_url}: {model_info}")
                            continue

                        # The server now sends parameter_schema, which is the new source of truth
                        parameter_schema = model_info.get("parameter_schema")

                        multimedia_model = MultimediaModel(
                            name=model_info["name"],
                            value=model_info["value"],
                            provider=MultimediaProvider(model_info["provider"]),
                            client_class=AutobyteusMultimediaClient,
                            runtime=MultimediaRuntime.AUTOBYTEUS,
                            host_url=host_url,
                            parameter_schema=parameter_schema
                        )
                        
                        MultimediaClientFactory.register_model(multimedia_model)
                        host_registered_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to register multimedia model '{model_info.get('name')}' from {host_url}: {e}")
                
                if host_registered_count > 0:
                    logger.info(f"Registered {host_registered_count} multimedia models from Autobyteus host {host_url}")
                total_registered_count += host_registered_count
            
            if total_registered_count > 0:
                 logger.info(f"Finished Autobyteus multimedia discovery. Total models registered: {total_registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during Autobyteus multimedia model discovery: {e}", exc_info=True)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
