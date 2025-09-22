import logging
from typing import Dict, Any, List
import os
from urllib.parse import urlparse

from autobyteus_llm_client import AutobyteusClient
from autobyteus.multimedia.image.api.autobyteus_image_client import AutobyteusImageClient
from autobyteus.multimedia.image.image_model import ImageModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime

logger = logging.getLogger(__name__)

class AutobyteusImageModelProvider:
    """
    Discovers and registers image models from remote Autobyteus server instances.
    """
    DEFAULT_SERVER_URL = 'http://localhost:8000'

    @staticmethod
    def _get_hosts() -> List[str]:
        """
        Gets Autobyteus server hosts from env vars. Skips discovery if no host is configured.
        """
        hosts_str = os.getenv('AUTOBYTEUS_LLM_SERVER_HOSTS')
        if hosts_str:
            return [host.strip() for host in hosts_str.split(',')]
        
        legacy_host = os.getenv('AUTOBYTEUS_LLM_SERVER_URL')
        if legacy_host:
            return [legacy_host]
            
        return []

    @staticmethod
    def discover_and_register():
        """Discover and register image models from all configured hosts."""
        try:
            from autobyteus.multimedia.image.image_client_factory import ImageClientFactory

            hosts = AutobyteusImageModelProvider._get_hosts()
            if not hosts:
                logger.info("No Autobyteus server hosts configured. Skipping Autobyteus image model discovery.")
                return

            total_registered_count = 0

            for host_url in hosts:
                if not AutobyteusImageModelProvider.is_valid_url(host_url):
                    logger.error(f"Invalid Autobyteus host URL for image model discovery: {host_url}, skipping.")
                    continue
                
                logger.info(f"Discovering image models from host: {host_url}")
                client = None
                try:
                    client = AutobyteusClient(server_url=host_url)
                    response = client.get_available_image_models_sync()
                except Exception as e:
                    logger.warning(f"Could not fetch models from Autobyteus server at {host_url}: {e}")
                    continue
                finally:
                    if client:
                        client.sync_client.close()

                if not response.get('models'):
                    logger.info(f"No image models found on host {host_url}.")
                    continue

                models = response.get('models', [])
                host_registered_count = 0
                for model_info in models:
                    try:
                        if not all(k in model_info for k in ["name", "value", "provider"]):
                            logger.warning(f"Skipping malformed image model from {host_url}: {model_info}")
                            continue

                        # Heuristic to ensure it's an image model if the server doesn't specify modality
                        if "parameter_schema" not in model_info:
                             logger.debug(f"Skipping model from {host_url} as it lacks a parameter schema, likely not an image model: {model_info.get('name')}")
                             continue

                        image_model = ImageModel(
                            name=model_info["name"],
                            value=model_info["value"],
                            provider=MultimediaProvider(model_info["provider"]),
                            client_class=AutobyteusImageClient,
                            runtime=MultimediaRuntime.AUTOBYTEUS,
                            host_url=host_url,
                            parameter_schema=model_info.get("parameter_schema")
                        )
                        
                        ImageClientFactory.register_model(image_model)
                        host_registered_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to register image model '{model_info.get('name')}' from {host_url}: {e}")
                
                if host_registered_count > 0:
                    logger.info(f"Registered {host_registered_count} image models from Autobyteus host {host_url}")
                total_registered_count += host_registered_count
            
            if total_registered_count > 0:
                 logger.info(f"Finished Autobyteus image model discovery. Total models registered: {total_registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during Autobyteus image model discovery: {e}", exc_info=True)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
