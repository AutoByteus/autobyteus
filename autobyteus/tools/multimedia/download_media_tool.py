import os
import logging
import mimetypes
import aiohttp
from typing import Optional, TYPE_CHECKING
from urllib.parse import urlparse

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_category import ToolCategory
from autobyteus.utils.file_utils import get_default_download_folder
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class DownloadMediaTool(BaseTool):
    """
    A unified tool to download any media file (e.g., image, PDF, audio) from a URL.
    """
    CATEGORY = ToolCategory.MULTIMEDIA

    @classmethod
    def get_name(cls) -> str:
        return "download_media"

    @classmethod
    def get_description(cls) -> str:
        return (
            "Downloads various media files (e.g., images like PNG/JPG, documents like PDF, audio like MP3/WAV) "
            "from a direct URL and saves them locally. It intelligently determines the correct file extension "
            "based on the content type. Returns the absolute path to the downloaded file."
        )

    @classmethod
    def get_argument_schema(cls) -> ParameterSchema:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The direct URL of the media file to download.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="filename",
            param_type=ParameterType.STRING,
            description="The desired base name for the downloaded file (e.g., 'vacation_photo', 'annual_report'). The tool will automatically add the correct file extension.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="folder",
            param_type=ParameterType.STRING,
            description="Optional. A custom directory path to save the file. If not provided, the system's default download folder will be used.",
            required=False
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, filename: str, folder: Optional[str] = None) -> str:
        # 1. Determine download directory
        try:
            if folder:
                # Security: prevent path traversal attacks.
                if ".." in folder:
                    raise ValueError("Security error: 'folder' path cannot contain '..'.")
                destination_dir = os.path.abspath(folder)
            else:
                destination_dir = get_default_download_folder()
            
            os.makedirs(destination_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error preparing download directory '{folder or 'default'}': {e}", exc_info=True)
            raise IOError(f"Failed to create or access download directory: {e}")

        # 2. Sanitize filename provided by the LLM
        if not filename or ".." in filename or os.path.isabs(filename) or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename. It must be a simple name without any path characters ('..', '/', '\\').")

        logger.info(f"Attempting to download from {url} to save as '{filename}' in '{destination_dir}'.")

        # 3. Download and process file asynchronously
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=60) as response:
                    response.raise_for_status()

                    # 4. Intelligently determine file extension from Content-Type header
                    content_type = response.headers.get('Content-Type')
                    correct_ext = ''
                    if content_type:
                        mime_type = content_type.split(';')[0].strip()
                        guess = mimetypes.guess_extension(mime_type)
                        if guess:
                            correct_ext = guess
                            logger.debug(f"Determined extension '{correct_ext}' from Content-Type: '{mime_type}'")

                    # Fallback to URL extension if Content-Type is generic or missing
                    if not correct_ext or correct_ext == '.bin':
                        url_path = urlparse(url).path
                        _, ext_from_url = os.path.splitext(os.path.basename(url_path))
                        if ext_from_url and len(ext_from_url) > 1: # Ensure it's not just a dot
                            logger.debug(f"Using fallback extension '{ext_from_url}' from URL.")
                            correct_ext = ext_from_url
                    
                    if not correct_ext:
                        logger.warning("Could not determine a file extension. The file will be saved without one.")
                    
                    # 5. Construct final filename and path
                    base_filename, _ = os.path.splitext(filename)
                    final_filename = f"{base_filename}{correct_ext}"
                    save_path = os.path.join(destination_dir, final_filename)
                    
                    # Ensure filename is unique to avoid overwriting
                    counter = 1
                    while os.path.exists(save_path):
                        final_filename = f"{base_filename}_{counter}{correct_ext}"
                        save_path = os.path.join(destination_dir, final_filename)
                        counter += 1
                    
                    # 6. Stream file content to disk
                    with open(save_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

                    logger.info(f"Successfully downloaded and saved file to: {save_path}")
                    return f"Successfully downloaded file to: {save_path}"

        except aiohttp.ClientError as e:
            logger.error(f"Network error while downloading from {url}: {e}", exc_info=True)
            raise ConnectionError(f"Failed to download from {url}: {e}")
        except IOError as e:
            logger.error(f"Failed to write downloaded file to {destination_dir}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during download from {url}: {e}", exc_info=True)
            raise RuntimeError(f"An unexpected error occurred: {e}")
