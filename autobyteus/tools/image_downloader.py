import os
import aiohttp
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig 
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from PIL import Image
from io import BytesIO
from autobyteus.utils.file_utils import get_default_download_folder
from autobyteus.events.event_types import EventType

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
        
        # Explicitly subscribe the handler in the constructor
        self.subscribe(EventType.WEIBO_POST_COMPLETED, self.on_weibo_post_completed)

        logger.debug(f"ImageDownloader initialized with download_folder: {self.download_folder}")

    @classmethod
    def get_description(cls) -> str:
        return f"Downloads an image from a given URL. Supported formats: {', '.join(format.upper()[1:] for format in cls.supported_formats)}."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="url", param_type=ParameterType.STRING, description=f"A direct URL to an image file (must end with {', '.join(cls.supported_formats)}).", required=True))
        schema.add_parameter(ParameterDefinition(name="folder", param_type=ParameterType.STRING, description="Optional. Custom directory path to save this specific image. Overrides instance default.", required=False))
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: 
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(name="custom_download_folder", param_type=ParameterType.STRING, description="Custom directory path where downloaded images will be saved by default.", required=False, default_value=None))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, folder: Optional[str] = None) -> str:
        current_download_folder = folder or self.download_folder
        if not any(url.lower().endswith(fmt) for fmt in self.supported_formats):
            raise ValueError(f"Unsupported image format. URL must end with one of: {', '.join(self.supported_formats)}.")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status() 
                    image_bytes = await response.read()

            with Image.open(BytesIO(image_bytes)) as img:
                img.verify() 

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = os.path.splitext(url)[1].lower() or ".png"

            filename = f"downloaded_image_{timestamp}{extension}"
            filepath = os.path.join(current_download_folder, filename)

            os.makedirs(current_download_folder, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

            self.last_downloaded_image = filepath 
            logger.info(f"The image is downloaded and stored at: {filepath}")
            self.emit(EventType.IMAGE_DOWNLOADED, image_path=filepath)
            return f"The image is downloaded and stored at: {filepath}"
        except Exception as e:
            logger.error(f"Error processing image from {url}: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing image from {url}: {str(e)}")

    def on_weibo_post_completed(self): # No **kwargs needed due to intelligent dispatch
        if self.last_downloaded_image and os.path.exists(self.last_downloaded_image):
            try:
                os.remove(self.last_downloaded_image)
                logger.info(f"Removed downloaded image: {self.last_downloaded_image} after Weibo post.")
            except Exception as e:
                logger.error(f"Failed to remove downloaded image: {self.last_downloaded_image}. Error: {str(e)}", exc_info=True)
        else:
            logger.debug("No last downloaded image to remove or image file not found.")
        self.last_downloaded_image = None
