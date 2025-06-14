from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from brui_core.ui_integrator import UIIntegrator
import os
import logging 
from urllib.parse import urljoin, urlparse 
from typing import Optional, TYPE_CHECKING, Any, List 

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__) 

class WebPageImageDownloader(BaseTool, UIIntegrator):
    """
    A class that downloads images (excluding SVGs and data URIs) from a given webpage URL using Playwright.
    Saves images to a specified directory.
    """
    def __init__(self, config: Optional[ToolConfig] = None): 
        BaseTool.__init__(self, config=config)
        UIIntegrator.__init__(self)
        logger.debug("WebPageImageDownloader tool initialized.")

    @classmethod
    def get_description(cls) -> str:
        return ("Downloads all usable images (excluding SVGs and data URIs) from a webpage URL. "
                "Saves them to a specified local directory and returns a list of saved file paths.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The URL of the webpage from which to download images.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="save_dir",
            param_type=ParameterType.STRING,
            description="The local directory path where downloaded images will be saved.",
            required=True
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, save_dir: str) -> List[str]: 
        logger.info(f"WebPageImageDownloader for agent {context.agent_id} downloading images from '{url}' to '{save_dir}'.")
        
        if not self._is_valid_page_url(url):
            raise ValueError(f"Invalid page URL format: {url}. Must be a full URL (e.g., http/https).")

        os.makedirs(save_dir, exist_ok=True)

        saved_paths: List[str] = []
        try:
            await self.initialize()
            if not self.page:
                 logger.error("Playwright page not initialized in WebPageImageDownloader.")
                 raise RuntimeError("Playwright page not available for WebPageImageDownloader.")

            await self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            image_srcs: List[str] = await self._get_image_srcs_from_page()
            logger.debug(f"Found {len(image_srcs)} image sources on page {url}.")
            
            download_counter = 0
            for i, img_src in enumerate(image_srcs):
                if not img_src or img_src.startswith("data:"): 
                    logger.debug(f"Skipping image source (data URI or empty): {img_src[:50]}...")
                    continue

                full_image_url = urljoin(self.page.url, img_src) 

                if self._is_svg(full_image_url):
                    logger.debug(f"Skipping SVG image: {full_image_url}")
                    continue
                
                if not self._is_valid_http_url(full_image_url):
                    logger.warning(f"Skipping invalid or non-HTTP(S) image URL: {full_image_url}")
                    continue

                file_path = self._generate_file_path(save_dir, download_counter, full_image_url)
                try:
                    image_response = await self.page.request.get(full_image_url)
                    if image_response.ok:
                        image_buffer = await image_response.body()
                        with open(file_path, "wb") as f:
                            f.write(image_buffer)
                        saved_paths.append(os.path.abspath(file_path))
                        logger.info(f"Downloaded image {download_counter + 1}: {full_image_url} to {file_path}")
                        download_counter += 1
                    else:
                        logger.warning(f"Failed to download image {full_image_url}, status: {image_response.status}")

                except Exception as dl_exc:
                    logger.error(f"Error downloading image {full_image_url}: {dl_exc}", exc_info=True)
            
            logger.info(f"Finished downloading images. Total saved: {len(saved_paths)}.")
            return saved_paths

        except Exception as e:
            logger.error(f"Error in WebPageImageDownloader for URL '{url}': {e}", exc_info=True)
            raise RuntimeError(f"WebPageImageDownloader failed for URL '{url}': {str(e)}")
        finally:
            await self.close()

    async def _get_image_srcs_from_page(self) -> List[str]:
        image_elements_data = await self.page.evaluate("""() => {
            const sources = new Set();
            document.querySelectorAll('img').forEach(img => {
                if (img.src && !img.src.startsWith('data:')) sources.add(img.src);
                if (img.srcset) {
                    img.srcset.split(',').forEach(part => {
                        const url = part.trim().split(' ')[0];
                        if (url && !url.startsWith('data:')) sources.add(url);
                    });
                }
                const dataSrc = img.getAttribute('data-src');
                if (dataSrc && !dataSrc.startsWith('data:')) sources.add(dataSrc);
            });
            return Array.from(sources);
        }""")
        return image_elements_data if image_elements_data else []
    
    def _is_valid_page_url(self, url_string: str) -> bool:
        try:
            result = urlparse(url_string)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except ValueError:
            return False
            
    def _is_valid_http_url(self, url_string: str) -> bool:
        try:
            result = urlparse(url_string)
            return result.scheme in ['http', 'https']
        except ValueError:
            return False

    def _is_svg(self, url: str) -> bool:
        return url.lower().split('?')[0].endswith('.svg') 

    def _generate_file_path(self, directory: str, index: int, url: str) -> str:
        try:
            parsed_url = urlparse(url)
            base_filename = os.path.basename(parsed_url.path)
            filename_stem, ext = os.path.splitext(base_filename)
            if not ext: 
                ext = ".jpg" 
            
            import string
            valid_chars_fs = "-_.() %s%s" % (string.ascii_letters, string.digits)
            safe_stem = ''.join(c for c in filename_stem if c in valid_chars_fs)[:50] 
            if not safe_stem: safe_stem = f"image_{index}"

            final_filename = f"{safe_stem}{ext}"

        except Exception: 
            final_filename = f"image_{index}.jpg" 
            
        return os.path.join(directory, final_filename)
