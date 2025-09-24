import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from autobyteus_llm_client import AutobyteusClient
from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.utils.response_types import SpeechGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.audio_model import AudioModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class AutobyteusAudioClient(BaseAudioClient):
    """
    An audio client that connects to an Autobyteus server instance for audio tasks.
    """

    def __init__(self, model: "AudioModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        if not model.host_url:
            raise ValueError("AutobyteusAudioClient requires a host_url in its AudioModel.")
        
        self.autobyteus_client = AutobyteusClient(server_url=model.host_url)
        logger.info(f"AutobyteusAudioClient initialized for model '{model.name}' on host '{model.host_url}'.")

    async def generate_speech(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpeechGenerationResponse:
        """
        Generates speech by calling the generate_speech endpoint on the remote Autobyteus server.
        """
        try:
            logger.info(f"Sending speech generation request for model '{self.model.name}' to {self.model.host_url}")
            
            model_name_for_server = self.model.name

            # Note: The underlying autobyteus_client.generate_speech does not currently accept **kwargs.
            # They are accepted here for interface consistency and future-proofing.
            response_data = await self.autobyteus_client.generate_speech(
                model_name=model_name_for_server,
                prompt=prompt,
                generation_config=generation_config
            )
            
            audio_urls = response_data.get("audio_urls", [])
            if not audio_urls:
                raise ValueError("Remote Autobyteus server did not return any audio URLs.")
                
            return SpeechGenerationResponse(audio_urls=audio_urls)
            
        except Exception as e:
            logger.error(f"Error calling Autobyteus server for speech generation: {e}", exc_info=True)
            raise

    async def cleanup(self):
        """Closes the underlying AutobyteusClient."""
        if self.autobyteus_client:
            await self.autobyteus_client.close()
        logger.debug("AutobyteusAudioClient cleaned up.")
