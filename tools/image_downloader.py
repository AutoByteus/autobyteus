# File: autobyteus/tools/image_downloader.py

import os
import aiohttp
import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from PIL import Image # For image validation
from io import BytesIO
from autobyteus.utils.file_utils import get_default_download_folder
from autobyteus.events.event_types import EventType
from autobyteus.events.decorators import event_listener

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class ImageDownloader(BaseTool):
    # Define supported_formats as a class variable so it can be accessed in class methods
    supported_formats = ['.jpeg', '.jpg', '.gif', '.png', '.webp']
    
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__()
        
        # Extract configuration with defaults
        custom_download_folder = None
        if config:
            custom_download_folder_val = config.get('custom_download_folder')
            if custom_download_folder_val and isinstance(custom_download_folder_val, str):
                 custom_download_folder = custom_download_folder_val
            elif custom_download_folder_val:
                 logger.warning(f"Invalid type for 'custom_download_folder' in ImageDownloader config: {type(custom_download_folder_val)}. Using default.")

        
        self.default_download_folder = get_default_download_folder()
        self.download_folder = custom_download_folder or self.default_download_folder
        # self.supported_formats instance variable removed, use class variable directly
        self.last_downloaded_image: Optional[str] = None # Ensure type hint
        
        logger.debug(f"ImageDownloader initialized with download_folder: {self.download_folder}")

    @classmethod
    def get_config_schema(cls) -> 'ToolConfigSchema':
        """
        Return the configuration schema for this tool.
        
        Returns:
            ToolConfigSchema: Schema describing the tool's configuration parameters.
        """
        schema = ToolConfigSchema()
        
        schema.add_parameter(ToolConfigParameter(
            name="custom_download_folder",
            param_type=ParameterType.DIRECTORY_PATH,
            description="Custom directory path where downloaded images will be saved. If not specified, uses the default download folder.",
            required=False,
            default_value=None # Default is handled in __init__ logic
        ))
        
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the ImageDownloader tool.

        Returns:
            str: An XML description of how to use the ImageDownloader tool.
        """
        return f'''ImageDownloader: Downloads an image from a given URL.

Usage:
<command name="ImageDownloader">
    <arg name="url">image_url</arg>
    <arg name="folder" optional="true">/custom/path/to/save</arg> <!-- Optional custom folder for this specific call -->
</command>

Parameters:
- "image_url": A string containing a direct URL to an image file (must end with {', '.join(cls.supported_formats)})
- "folder" (optional): A string specifying a custom download folder for this specific execution. If not provided, the tool's configured download folder is used.

Supported image formats: {', '.join(format.upper()[1:] for format in cls.supported_formats)}

Positive examples:
<command name="ImageDownloader">
    <arg name="url">https://example.com/photo.jpg</arg>
</command>

<command name="ImageDownloader">
    <arg name="url">https://example.com/image.png</arg>
    <arg name="folder">/tmp/my_images</arg>
</command>

Negative examples (These will not work):
<command name="ImageDownloader">
    <arg name="url">https://example.com/page_containing_image.html</arg>
</command>

<command name="ImageDownloader">
    <arg name="url">https://example.com/image_without_extension</arg>
</command>

Note: The URL must be a direct link to the image file, not a webpage containing the image.'''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        custom_folder_arg = kwargs.get('folder') # Folder override from arguments
        current_download_folder = custom_folder_arg or self.download_folder

        logger.info(f"Agent '{context.agent_id}' downloading image from '{url}' to folder '{current_download_folder}'.")

        if not any(url.lower().endswith(fmt) for fmt in self.supported_formats):
            raise ValueError(
                f"Unsupported image format. The URL must end with one of the following extensions: "
                f"{', '.join(self.supported_formats)}. Provided URL: {url}"
            )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                    image_bytes = await response.read()

            # Validate image content
            try:
                with Image.open(BytesIO(image_bytes)) as img:
                    img.verify() # Verify that it is, in fact, an image.
                    # fmt = img.format # Not strictly needed if extension is trusted from URL
            except (IOError, SyntaxError) as img_err: # PIL.UnidentifiedImageError inherits from IOError
                logger.error(f"Agent '{context.agent_id}': Downloaded content from '{url}' is not a valid image or is corrupted: {img_err}")
                raise ValueError(f"Downloaded content from '{url}' is not a valid image or is corrupted.")


            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f") # Added microseconds for more uniqueness
            extension = os.path.splitext(url)[1].lower()
            # Sanitize filename part from URL if present, or use a generic name
            url_filename_part = os.path.basename(url)
            url_filename_stem = os.path.splitext(url_filename_part)[0]
            safe_filename_stem = "".join(c if c.isalnum() else "_" for c in url_filename_stem[:30]) # Sanitize and shorten
            
            filename = f"{safe_filename_stem}_{timestamp}{extension}"
            filepath = os.path.join(current_download_folder, filename)

            os.makedirs(current_download_folder, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)

            self.last_downloaded_image = filepath # Store for potential cleanup
            absolute_filepath = os.path.abspath(filepath)
            logger.info(f"Agent '{context.agent_id}': Image downloaded and stored at: {absolute_filepath}")
            return f"The image is downloaded and stored at: {absolute_filepath}"
        
        except aiohttp.ClientError as e:
            logger.error(f"Agent '{context.agent_id}': Failed to download image from {url}. Error: {str(e)}")
            raise ValueError(f"Failed to download image from {url}. ClientError: {str(e)}") # Re-raise specific error
        except ValueError as ve: # Catch ValueError from image validation or format check
             logger.error(f"Agent '{context.agent_id}': Error processing image from {url}. Error: {str(ve)}")
             raise # Re-raise
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"Agent '{context.agent_id}': Unexpected error processing image from {url}. Error: {str(e)}", exc_info=True)
            raise ValueError(f"Unexpected error processing image from {url}: {str(e)}")


    @event_listener(EventType.WEIBO_POST_COMPLETED)
    def on_weibo_post_completed(self, *args, **kwargs): # pragma: no cover
        # This event listener logic is specific and might be conditional on context (e.g., agent_id)
        # For now, keeping it simple as in original.
        agent_id_from_event = kwargs.get('agent_id', 'UnknownAgent')
        
        # Only clean up if this tool instance's agent_id matches the event's agent_id, if self.agent_id is set
        if self.agent_id and self.agent_id != agent_id_from_event:
            logger.debug(f"ImageDownloader for agent '{self.agent_id}' ignoring WEIBO_POST_COMPLETED event for agent '{agent_id_from_event}'.")
            return

        if self.last_downloaded_image and os.path.exists(self.last_downloaded_image):
            try:
                os.remove(self.last_downloaded_image)
                logger.info(f"Agent '{self.agent_id or agent_id_from_event}': Removed downloaded image after Weibo post: {self.last_downloaded_image}")
            except Exception as e:
                logger.error(f"Agent '{self.agent_id or agent_id_from_event}': Failed to remove downloaded image: {self.last_downloaded_image}. Error: {str(e)}")
        else:
            logger.debug(f"Agent '{self.agent_id or agent_id_from_event}': No image to remove or image file not found for WEIBO_POST_COMPLETED event.")
        self.last_downloaded_image = None
