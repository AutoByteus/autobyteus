import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from autobyteus_llm_client import AutobyteusClient
from autobyteus.multimedia.image.base_image_client import BaseImageClient
from autobyteus.multimedia.utils.response_types import ImageGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.image.image_model import ImageModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)

class AutobyteusImageClient(BaseImageClient):
    """
    An image client that connects to an Autobyteus LLM server instance for image tasks.
    """

    def __init__(self, model: "ImageModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        if not model.host_url:
            raise ValueError("AutobyteusImageClient requires a host_url in its ImageModel.")
        
        self.autobyteus_client = AutobyteusClient(server_url=model.host_url)
        logger.info(f"AutobyteusImageClient initialized for model '{self.model.name}' on host '{model.host_url}'.")

    async def generate_image(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Generates an image by calling the generate_image endpoint on the remote Autobyteus server.
        """
        # The remote server handles both generation and editing through one endpoint.
        # This method is a unified entry point.
        return await self._call_remote_generate(
            prompt=prompt,
            input_image_urls=input_image_urls,
            mask_url=None, # Not used in pure generation
            generation_config=generation_config,
            **kwargs
        )

    async def edit_image(
        self,
        prompt: str,
        input_image_urls: List[str],
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ImageGenerationResponse:
        """
        Edits an image by calling the generate_image endpoint on the remote Autobyteus server.
        """
        return await self._call_remote_generate(
            prompt=prompt,
            input_image_urls=input_image_urls,
            mask_url=mask_url,
            generation_config=generation_config,
            **kwargs
        )
    
    async def _call_remote_generate(
        self,
        prompt: str,
        input_image_urls: Optional[List[str]],
        mask_url: Optional[str],
        generation_config: Optional[Dict[str, Any]],
        **kwargs
    ) -> ImageGenerationResponse:
        """Internal helper to call the remote server."""
        try:
            logger.info(f"Sending image generation request for model '{self.model.name}' to {self.model.host_url}")
            
            # The model name for the remote server is the `value`, not the unique `model_identifier`
            model_name_for_server = self.model.name

            # Note: The underlying autobyteus_client.generate_image does not currently accept **kwargs.
            # They are accepted here for interface consistency and future-proofing.
            response_data = await self.autobyteus_client.generate_image(
                model_name=model_name_for_server,
                prompt=prompt,
                input_image_urls=input_image_urls,
                mask_url=mask_url,
                generation_config=generation_config
            )
            
            image_urls = response_data.get("image_urls", [])
            if not image_urls:
                raise ValueError("Remote Autobyteus server did not return any image URLs.")
                
            return ImageGenerationResponse(image_urls=image_urls)
            
        except Exception as e:
            logger.error(f"Error calling Autobyteus server for image generation: {e}")
            raise

    async def cleanup(self):
        """Closes the underlying AutobyteusClient."""
        if self.autobyteus_client:
            await self.autobyteus_client.close()
        logger.debug("AutobyteusImageClient cleaned up.")
