import logging
import os
from typing import List
from urllib.parse import urlparse

from autobyteus.clients import AutobyteusClient
from autobyteus.multimedia.providers import MultimediaProvider
from autobyteus.multimedia.runtimes import MultimediaRuntime
from autobyteus.multimedia.video.api.autobyteus_video_client import AutobyteusVideoClient
from autobyteus.multimedia.video.video_model import VideoModel

logger = logging.getLogger(__name__)


class AutobyteusVideoModelProvider:
    """
    Discovers and registers video models from remote Autobyteus server instances.
    """
    DEFAULT_SERVER_URL = "http://localhost:8000"

    @staticmethod
    def _get_hosts() -> List[str]:
        """
        Gets Autobyteus server hosts from env vars. Skips discovery if no host is configured.
        """
        hosts_str = os.getenv("AUTOBYTEUS_LLM_SERVER_HOSTS")
        if hosts_str:
            return [host.strip() for host in hosts_str.split(",") if host.strip()]

        return []

    @staticmethod
    def discover_and_register():
        """Discover and register video models from all configured hosts."""
        try:
            from autobyteus.multimedia.video.video_client_factory import VideoClientFactory

            hosts = AutobyteusVideoModelProvider._get_hosts()
            if not hosts:
                logger.info("No Autobyteus server hosts configured. Skipping Autobyteus video model discovery.")
                return

            total_registered_count = 0

            for host_url in hosts:
                if not AutobyteusVideoModelProvider.is_valid_url(host_url):
                    logger.error("Invalid Autobyteus host URL for video model discovery: %s, skipping.", host_url)
                    continue

                logger.info("Discovering video models from host: %s", host_url)
                client = None
                try:
                    client = AutobyteusClient(server_url=host_url)
                    response = client.get_available_video_models_sync()
                except Exception as e:
                    logger.warning("Could not fetch video models from Autobyteus server at %s: %s", host_url, e)
                    continue
                finally:
                    if client:
                        client.sync_client.close()

                if not response.get("models"):
                    logger.info("No video models found on host %s.", host_url)
                    continue

                models = response.get("models", [])
                host_registered_count = 0
                for model_info in models:
                    try:
                        if not all(k in model_info for k in ["name", "value", "provider"]):
                            logger.warning("Skipping malformed video model from %s: %s", host_url, model_info)
                            continue

                        if "parameter_schema" not in model_info:
                            logger.debug(
                                "Skipping model from %s as it lacks a parameter schema, likely not a video model: %s",
                                host_url,
                                model_info.get("name"),
                            )
                            continue

                        video_model = VideoModel(
                            name=model_info["name"],
                            value=model_info["value"],
                            provider=MultimediaProvider(model_info["provider"]),
                            client_class=AutobyteusVideoClient,
                            runtime=MultimediaRuntime.AUTOBYTEUS,
                            host_url=host_url,
                            parameter_schema=model_info.get("parameter_schema"),
                            description=model_info.get("description"),
                        )

                        VideoClientFactory.register_model(video_model)
                        host_registered_count += 1

                    except Exception as e:
                        logger.error(
                            "Failed to register video model '%s' from %s: %s",
                            model_info.get("name"),
                            host_url,
                            e,
                        )

                if host_registered_count > 0:
                    logger.info("Registered %s video models from Autobyteus host %s", host_registered_count, host_url)
                total_registered_count += host_registered_count

            if total_registered_count > 0:
                logger.info(
                    "Finished Autobyteus video model discovery. Total models registered: %s",
                    total_registered_count,
                )

        except Exception as e:
            logger.error("An unexpected error occurred during Autobyteus video model discovery: %s", e, exc_info=True)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
