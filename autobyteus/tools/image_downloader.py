# File: autobyteus/tools/image_downloader.py

import os
import aiohttp
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from PIL import Image # Pillow
from io import BytesIO
from autobyteus.utils.file_utils import get_default_download_folder
from autobyteus.events.event_types import EventType
from autobyteus.events.decorators import event_listener

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__)

class ImageDownloader(BaseTool):
    supported_formats = ['.jpeg', '.jpg', '.gif', '.png', '.webp']
    
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        
        custom_download_folder = None
        if config:
            custom_download_folder = config.get('custom_download_folder')
        
        self.default_download_folder = get_default_download_folder()
        self.download_folder = custom_download_folder or self.default_download_folder
        self.last_downloaded_image = None
        
        logger.debug(f"ImageDownloader initialized with download_folder: {self.download_folder}")

    @classmethod
    def get_description(cls) -> str:
        return f"Downloads an image from a given URL. Supported formats: {', '.join(format.upper()[1:] for format in cls.supported_formats)}."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(
            ParameterDefinition(
                name="url",
                param_type=ParameterType.STRING, 
                description=f"A direct URL to an image file (must end with {', '.join(cls.supported_formats)}).",
                required=True
            )
        )
        schema.add_parameter(
            ParameterDefinition(
                name="folder", 
                param_type=ParameterType.STRING,
                description="Optional. Custom directory path to save this specific image. Overrides instance default.",
                required=False 
            )
        )
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="custom_download_folder",
            param_type=ParameterType.STRING,
            description="Custom directory path where downloaded images will be saved by default. If not specified, uses the system's default download folder.",
            required=False,
            default_value=None 
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, folder: Optional[str] = None) -> str:
        logger.debug(f"ImageDownloader executing for agent {context.agent_id} with URL: {url}, Folder: {folder}")

        current_download_folder = folder or self.download_folder

        if not any(url.lower().endswith(fmt) for fmt in self.supported_formats):
            raise ValueError(
                f"Unsupported image format or malformed URL. The URL must end with one of the following extensions: "
                f"{', '.join(self.supported_formats)}. Provided URL: {url}"
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status() 
                    image_bytes = await response.read()

            with Image.open(BytesIO(image_bytes)) as img:
                img.verify() 

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = os.path.splitext(url)[1].lower() 
            if not extension or extension not in self.supported_formats: 
                extension = ".png" 
                logger.warning(f"Could not determine valid extension from URL '{url}', defaulting to '.png'")

            filename = f"downloaded_image_{timestamp}{extension}"
            filepath = os.path.join(current_download_folder, filename)

            os.makedirs(current_download_folder, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

            self.last_downloaded_image = filepath 
            logger.info(f"The image is downloaded and stored at: {filepath}")
            self.emit(EventType.IMAGE_DOWNLOADED, image_path=filepath)
            return f"The image is downloaded and stored at: {filepath}"
        except aiohttp.ClientError as e:
            logger.error(f"Failed to download image from {url}. Network error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to download image from {url}. Network error: {str(e)}")
        except Image.UnidentifiedImageError: 
            logger.error(f"Failed to identify image from {url}. The content might not be a valid image or is corrupted.", exc_info=True)
            raise ValueError(f"The content from {url} is not a valid or supported image format.")
        except Exception as e:
            logger.error(f"Error processing image from {url}. Error: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing image from {url}. Unexpected error: {str(e)}")

    @event_listener(EventType.WEIBO_POST_COMPLETED)
    def on_weibo_post_completed(self, *args: Any, **kwargs: Any) -> None: 
        if self.last_downloaded_image and os.path.exists(self.last_downloaded_image):
            try:
                os.remove(self.last_downloaded_image)
                logger.info(f"Removed downloaded image: {self.last_downloaded_image} after Weibo post.")
            except Exception as e:
                logger.error(f"Failed to remove downloaded image: {self.last_downloaded_image}. Error: {str(e)}", exc_info=True)
        else:
            logger.debug("No last downloaded image to remove or image file not found.")
        self.last_downloaded_image = None
