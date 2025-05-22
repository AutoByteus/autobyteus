from typing import TYPE_CHECKING, Any, List
from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator
import os
from urllib.parse import urljoin, urlparse
import logging
import aiohttp # For robust image downloading

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class WebPageImageDownloader(BaseTool, UIIntegrator):
    """
    A class that downloads images (excluding SVGs) from a given webpage using Playwright.
    """
    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the WebPageImageDownloader tool.

        Returns:
            str: An XML description of how to use the WebPageImageDownloader tool.
        """
        return '''
    WebPageImageDownloader: Downloads images (excluding SVGs) from a given webpage and saves them to the specified directory. Usage:
    <command name="WebPageImageDownloader">
    <arg name="url">webpage_url</arg>
    <arg name="save_dir">path/to/save/directory</arg>
    </command>
    where "webpage_url" is a string containing the URL of the webpage to download images from, and "path/to/save/directory" is the directory where the images will be saved.
    Returns a list of absolute paths to the saved images.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> List[str]:
        url = kwargs.get('url')
        save_dir = kwargs.get('save_dir')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")
        if not save_dir:
            raise ValueError("The 'save_dir' keyword argument must be specified.")
        
        os.makedirs(save_dir, exist_ok=True)
        logger.info(f"Agent '{context.agent_id}' downloading images from '{url}' to '{save_dir}'.")

        await self.initialize()
        try:
            await self.page.goto(url, wait_until="networkidle")
            
            image_urls_from_page = await self._get_image_urls_from_page()
            
            saved_paths: List[str] = []
            async with aiohttp.ClientSession() as session:
                for i, image_relative_url in enumerate(image_urls_from_page):
                    full_image_url = urljoin(url, image_relative_url) # Resolve relative URLs
                    if not self._is_svg(full_image_url) and self._is_valid_image_url(full_image_url):
                        file_path = self._generate_file_path(save_dir, i, full_image_url)
                        try:
                            await self._download_and_save_image(session, full_image_url, file_path)
                            saved_paths.append(os.path.abspath(file_path))
                            logger.debug(f"Agent '{context.agent_id}' saved image to '{file_path}'.")
                        except Exception as e:
                            logger.warning(f"Agent '{context.agent_id}' failed to download/save image '{full_image_url}': {e}")
            
            logger.info(f"Agent '{context.agent_id}' completed image download. Saved {len(saved_paths)} images.")
            return saved_paths
        finally:
            await self.close()

    async def _get_image_urls_from_page(self) -> List[str]:
        image_urls = await self.page.evaluate("""() => {
            return Array.from(document.images).map(i => i.src).filter(src => src && src.trim() !== '');
        }""")
        return image_urls
    
    def _is_valid_image_url(self, url_string: str) -> bool:
        try:
            result = urlparse(url_string)
            return all([result.scheme, result.netloc, result.path])
        except:
            return False

    def _is_svg(self, url_string: str) -> bool:
        return url_string.lower().endswith('.svg')

    def _generate_file_path(self, directory: str, index: int, image_url: str) -> str:
        try:
            parsed_url = urlparse(image_url)
            base_filename = os.path.basename(parsed_url.path)
            if not base_filename: # Handle cases like "http://example.com/"
                base_filename = f"image_{index}"
            
            filename_stem, ext = os.path.splitext(base_filename)
            if not ext: # If no extension, try to guess or use default
                 ext = ".jpg" # Default extension if none found or non-standard
            
            # Sanitize filename_stem (simple sanitization)
            safe_stem = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in filename_stem)
            if not safe_stem: safe_stem = f"image_{index}" # fallback if stem becomes empty

            filename = f"{safe_stem[:50]}{ext}" # Truncate stem length
        except Exception:
            filename = f"image_{index}.jpg" # Fallback filename

        return os.path.join(directory, filename)

    async def _download_and_save_image(self, session: aiohttp.ClientSession, image_url: str, file_path: str) -> None:
        async with session.get(image_url) as response:
            response.raise_for_status() # Raise an exception for bad status codes
            image_data = await response.read()
            with open(file_path, "wb") as f:
                f.write(image_data)
