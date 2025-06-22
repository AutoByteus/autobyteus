from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from brui_core.ui_integrator import UIIntegrator
import os
import logging
from typing import Optional, TYPE_CHECKING, Any 
from urllib.parse import urlparse 

from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class WebPagePDFGenerator(BaseTool, UIIntegrator):
    """
    A class that generates a PDF of a given webpage URL using Playwright.
    Saves the PDF to a specified directory. This is a standalone browser tool.
    """
    def __init__(self, config: Optional[ToolConfig] = None): 
        BaseTool.__init__(self, config=config)
        UIIntegrator.__init__(self)
        logger.debug("WebPagePDFGenerator (standalone) tool initialized.")

    @classmethod
    def get_description(cls) -> str:
        return ("Generates a PDF (A4 format) of a given webpage URL. "
                "Saves it to a specified local directory and returns the absolute file path of the saved PDF.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The URL of the webpage to generate a PDF from.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="save_dir", 
            param_type=ParameterType.STRING,
            description="The local directory path where the generated PDF will be saved. A filename will be auto-generated.",
            required=True
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, save_dir: str) -> str: 
        logger.info(f"WebPagePDFGenerator for agent {context.agent_id} generating PDF for '{url}', saving to directory '{save_dir}'.")

        if not self._is_valid_page_url(url):
            raise ValueError(f"Invalid page URL format: {url}. Must be a full URL (e.g., http/https).")

        os.makedirs(save_dir, exist_ok=True) 

        try:
            parsed_url = urlparse(url)
            domain_part = parsed_url.netloc.replace('.', '_')
            path_part = parsed_url.path.strip('/').replace('/', '_').replace('.', '_')
            safe_url_part = f"{domain_part}_{path_part}"[:50] 
            if not safe_url_part: safe_url_part = "webpage"
        except Exception:
            safe_url_part = "webpage"
        
        import time
        timestamp = int(time.time())
        pdf_filename = f"{safe_url_part}_{timestamp}.pdf"
        full_file_path = os.path.join(save_dir, pdf_filename)

        try:
            await self.initialize()
            if not self.page:
                 logger.error("Playwright page not initialized in WebPagePDFGenerator.")
                 raise RuntimeError("Playwright page not available for WebPagePDFGenerator.")

            await self.page.goto(url, wait_until="networkidle", timeout=60000)
            
            await self.page.pdf(path=full_file_path, format='A4', print_background=True) 
            
            absolute_file_path = os.path.abspath(full_file_path)
            logger.info(f"PDF generated and saved successfully to {absolute_file_path}")
            return absolute_file_path
        except Exception as e:
            logger.error(f"Error generating PDF for URL '{url}': {e}", exc_info=True)
            raise RuntimeError(f"WebPagePDFGenerator failed for URL '{url}': {str(e)}")
        finally:
            await self.close() 

    def _is_valid_page_url(self, url_string: str) -> bool: 
        try:
            result = urlparse(url_string)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except ValueError:
            return False
