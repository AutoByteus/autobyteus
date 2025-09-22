import logging
from typing import List
import os
from urllib.parse import urlparse

from autobyteus_llm_client import AutobyteusClient
from autobyteus.multimedia.audio.api.autobyteus_audio_client import AutobyteusAudioClient
from autobyteus.multimedia.audio.audio_model import AudioModel
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime

logger = logging.getLogger(__name__)

class AutobyteusAudioModelProvider:
    """
    Discovers and registers audio models from remote Autobyteus server instances.
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
        """Discover and register audio models from all configured hosts."""
        try:
            from autobyteus.multimedia.audio.audio_client_factory import AudioClientFactory

            hosts = AutobyteusAudioModelProvider._get_hosts()
            if not hosts:
                logger.info("No Autobyteus server hosts configured. Skipping Autobyteus audio model discovery.")
                return

            total_registered_count = 0

            for host_url in hosts:
                if not AutobyteusAudioModelProvider.is_valid_url(host_url):
                    logger.error(f"Invalid Autobyteus host URL for audio model discovery: {host_url}, skipping.")
                    continue
                
                logger.info(f"Discovering audio models from host: {host_url}")
                client = None
                try:
                    client = AutobyteusClient(server_url=host_url)
                    response = client.get_available_audio_models_sync()
                except Exception as e:
                    logger.warning(f"Could not fetch audio models from Autobyteus server at {host_url}: {e}")
                    continue
                finally:
                    if client:
                        client.sync_client.close()

                if not response.get('models'):
                    logger.info(f"No audio models found on host {host_url}.")
                    continue

                models = response.get('models', [])
                host_registered_count = 0
                for model_info in models:
                    try:
                        if not all(k in model_info for k in ["name", "value", "provider"]):
                            logger.warning(f"Skipping malformed audio model from {host_url}: {model_info}")
                            continue

                        if "parameter_schema" not in model_info:
                             logger.debug(f"Skipping model from {host_url} as it lacks a parameter schema, likely not an audio model: {model_info.get('name')}")
                             continue

                        audio_model = AudioModel(
                            name=model_info["name"],
                            value=model_info["value"],
                            provider=MultimediaProvider(model_info["provider"]),
                            client_class=AutobyteusAudioClient,
                            runtime=MultimediaRuntime.AUTOBYTEUS,
                            host_url=host_url,
                            parameter_schema=model_info.get("parameter_schema")
                        )
                        
                        AudioClientFactory.register_model(audio_model)
                        host_registered_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to register audio model '{model_info.get('name')}' from {host_url}: {e}")
                
                if host_registered_count > 0:
                    logger.info(f"Registered {host_registered_count} audio models from Autobyteus host {host_url}")
                total_registered_count += host_registered_count
            
            if total_registered_count > 0:
                 logger.info(f"Finished Autobyteus audio model discovery. Total models registered: {total_registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during Autobyteus audio model discovery: {e}", exc_info=True)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
