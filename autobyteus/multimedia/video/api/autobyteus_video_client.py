import logging
import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from autobyteus.clients import AutobyteusClient
from autobyteus.multimedia.utils.response_types import VideoGenerationResponse
from autobyteus.multimedia.video.base_video_client import BaseVideoClient

if TYPE_CHECKING:
    from autobyteus.multimedia.video.video_model import VideoModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


class AutobyteusVideoClient(BaseVideoClient):
    """
    A video client that connects to an Autobyteus server instance for video tasks.
    Maintains a persistent session ID for stateful interactions.
    """

    def __init__(self, model: "VideoModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        if not model.host_url:
            raise ValueError("AutobyteusVideoClient requires a host_url in its VideoModel.")

        self.autobyteus_client = AutobyteusClient(server_url=model.host_url)
        self.session_id = str(uuid.uuid4())
        logger.info(
            "AutobyteusVideoClient initialized for model '%s' on host '%s' with session_id '%s'.",
            self.model.name,
            model.host_url,
            self.session_id,
        )

    async def generate_video(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        input_audio_urls: Optional[List[str]] = None,
        input_video_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> VideoGenerationResponse:
        """
        Generates a video by calling the generate_video endpoint on the remote Autobyteus server.
        """
        try:
            logger.info(
                "Sending video generation request for model '%s' to %s (Session: %s)",
                self.model.name,
                self.model.host_url,
                self.session_id,
            )

            response_data = await self.autobyteus_client.generate_video(
                model_name=self.model.name,
                prompt=prompt,
                input_image_urls=input_image_urls,
                input_audio_urls=input_audio_urls,
                input_video_urls=input_video_urls,
                generation_config=generation_config,
                session_id=self.session_id,
            )

            video_urls = response_data.get("video_urls", [])
            if not video_urls:
                raise ValueError("Remote Autobyteus server did not return any video URLs.")

            return VideoGenerationResponse(video_urls=video_urls)

        except Exception as e:
            logger.error("Error calling Autobyteus server for video generation: %s", e, exc_info=True)
            raise

    async def cleanup(self):
        """
        Notifies the server to cleanup the session, then closes the underlying HTTP client.
        """
        if self.autobyteus_client:
            try:
                logger.info("Notifying server to cleanup video session '%s'...", self.session_id)
                await self.autobyteus_client.cleanup_video_session(self.session_id)
            except Exception as e:
                logger.error("Failed to cleanup remote video session '%s': %s", self.session_id, e)
            finally:
                await self.autobyteus_client.close()

        logger.debug("AutobyteusVideoClient cleaned up.")
