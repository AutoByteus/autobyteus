# File: autobyteus/tools/pdf_downloader.py

import os
import requests # Using synchronous requests; consider aiohttp for full async if performance is critical
import logging
import asyncio # For asyncio.to_thread
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from autobyteus.utils.file_utils import get_default_download_folder

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class PDFDownloader(BaseTool):
    """
    A tool that downloads a PDF file from a given URL and saves it locally.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__()
        
        custom_download_folder = None
        if config:
            custom_download_folder_val = config.get('custom_download_folder')
            if custom_download_folder_val and isinstance(custom_download_folder_val, str):
                custom_download_folder = custom_download_folder_val
            elif custom_download_folder_val:
                logger.warning(f"Invalid type for 'custom_download_folder' in PDFDownloader config: {type(custom_download_folder_val)}. Using default.")
        
        self.default_download_folder = get_default_download_folder()
        self.download_folder = custom_download_folder or self.default_download_folder
        
        logger.debug(f"PDFDownloader initialized with download_folder: {self.download_folder}")

    @classmethod
    def get_config_schema(cls) -> 'ToolConfigSchema':
        """
        Return the configuration schema for this tool.
        """
        schema = ToolConfigSchema()
        schema.add_parameter(ToolConfigParameter(
            name="custom_download_folder",
            param_type=ParameterType.DIRECTORY_PATH,
            description="Custom directory path where downloaded PDF files will be saved. If not specified, uses the default download folder.",
            required=False,
            default_value=None # Default handled in __init__
        ))
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the PDFDownloader tool.
        """
        return '''PDFDownloader: Downloads a PDF file from a given URL. Usage:
    <command name="PDFDownloader">
    <arg name="url">https://example.com/file.pdf</arg>
    <arg name="folder" optional="true">/custom/path/to/save</arg> <!-- Optional custom folder for this specific call -->
    </command>
    Returns the absolute path to the saved PDF file.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        """
        Download a PDF file from the given URL and save it locally.

        Args:
            context: The AgentContext of the calling agent.
            **kwargs: Keyword arguments containing the URL.
                      'url': The URL of the PDF file to download.
                      'folder' (optional): Custom download folder path for this execution.

        Returns:
            str: A message indicating the result of the download operation, including the save path.

        Raises:
            ValueError: If the 'url' keyword argument is not specified or if content is not PDF.
            RuntimeError: For download or file I/O errors.
        """
        url = kwargs.get('url')
        custom_folder_arg = kwargs.get('folder') # Folder override from arguments
        current_download_folder = custom_folder_arg or self.download_folder

        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        agent_id = context.agent_id
        logger.info(f"Agent '{agent_id}' attempting to download PDF from '{url}' to folder '{current_download_folder}'.")

        def download_and_save_sync():
            try:
                response = requests.get(url, stream=True, timeout=30) # Added timeout
                response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)

                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/pdf' not in content_type:
                    # This check should be before extensive I/O
                    raise ValueError(f"The URL does not point to a PDF file. Content-Type: '{content_type}', URL: '{url}'")

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f") # Added microseconds
                # Create a more unique/descriptive filename if possible
                url_filename_part = os.path.basename(url)
                url_filename_stem = os.path.splitext(url_filename_part)[0]
                safe_filename_stem = "".join(c if c.isalnum() else "_" for c in url_filename_stem[:30])
                
                filename = f"{safe_filename_stem}_{timestamp}.pdf"
                save_path = os.path.join(current_download_folder, filename)

                os.makedirs(current_download_folder, exist_ok=True)
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                
                absolute_save_path = os.path.abspath(save_path)
                logger.info(f"Agent '{agent_id}': PDF successfully downloaded and saved to {absolute_save_path}")
                return f"PDF successfully downloaded and saved to {absolute_save_path}"
            
            except requests.exceptions.RequestException as e_req:
                error_message = f"Error downloading PDF from '{url}': {str(e_req)}"
                logger.error(f"Agent '{agent_id}': {error_message}", exc_info=True)
                raise RuntimeError(error_message) from e_req
            except ValueError as ve_val: # Catch specific ValueError from content type check
                logger.error(f"Agent '{agent_id}': {str(ve_val)}")
                raise # Re-raise
            except IOError as e_io:
                error_message = f"Error saving PDF to '{current_download_folder}': {str(e_io)}"
                logger.error(f"Agent '{agent_id}': {error_message}", exc_info=True)
                raise RuntimeError(error_message) from e_io
            except Exception as e_other: # Catch-all for unexpected errors during sync operation
                error_message = f"Unexpected error during PDF download/save for '{url}': {str(e_other)}"
                logger.error(f"Agent '{agent_id}': {error_message}", exc_info=True)
                raise RuntimeError(error_message) from e_other

        try:
            return await asyncio.to_thread(download_and_save_sync)
        except Exception as e: # Catch exceptions raised from the thread
            # The error should be logged within download_and_save_sync,
            # but this ensures it's caught if asyncio.to_thread itself fails or if an unhandled case exists.
            # BaseTool.execute will format this into a user-friendly error string if it's a RuntimeError/ValueError.
            raise 
