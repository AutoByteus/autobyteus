from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated
from brui_core.ui_integrator import UIIntegrator # Inherits from UIIntegrator
import logging # Added
import os # Added for path manipulations if any

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Added

logger = logging.getLogger(__name__) # Added

class WebPageScreenshotTaker(BaseTool, UIIntegrator):
    """
    A class that takes a screenshot of a given webpage using Playwright and saves it.
    Inherits from UIIntegrator for Playwright page access.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self) # Initialize UIIntegrator
        
        self.full_page: bool = True  
        self.image_format: str = "png"  
        
        if config:
            self.full_page = config.get('full_page', True)
            self.image_format = str(config.get('image_format', 'png')).lower()
            if self.image_format not in ["png", "jpeg"]:
                logger.warning(f"Invalid image_format '{self.image_format}' in config. Defaulting to 'png'.")
                self.image_format = "png"
        logger.debug(f"WebPageScreenshotTaker initialized. Full page: {self.full_page}, Format: {self.image_format}")

    @classmethod
    def get_description(cls) -> str:
        return "Takes a screenshot of a given webpage URL using Playwright and saves it to the specified file path. Returns the absolute path of the saved screenshot."

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="url",
            param_type=ParameterType.STRING,
            description="The URL of the webpage to take a screenshot of.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="file_path", # This is the argument name for execute
            param_type=ParameterType.FILE_PATH,
            description="The local file path (including filename and extension, e.g., 'screenshots/page.png') where the screenshot will be saved.",
            required=True
        ))
        # Instantiation config (full_page, image_format) are not args for execute here.
        # If they were to be overridden at execute time, they'd be added to this schema.
        return schema
        
    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: # For instantiation config
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="full_page",
            param_type=ParameterType.BOOLEAN,
            description="Whether to capture the full scrollable page content or just the visible viewport by default for this instance.",
            required=False,
            default_value=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="image_format",
            param_type=ParameterType.ENUM,
            description="Default image format for screenshots taken by this instance (png or jpeg).",
            required=False,
            default_value="png",
            enum_values=["png", "jpeg"]
        ))
        return schema

    async def _execute(self, context: 'AgentContext', url: str, file_path: str) -> str: # Updated signature
        """
        Take a screenshot of the webpage.
        'url' and 'file_path' are validated by BaseTool.execute().
        """
        logger.info(f"WebPageScreenshotTaker for agent {context.agent_id} taking screenshot of '{url}', saving to '{file_path}'.")
        
        # Ensure parent directory for file_path exists
        output_dir = os.path.dirname(file_path)
        if output_dir: # If file_path includes a directory
            os.makedirs(output_dir, exist_ok=True)

        try:
            await self.initialize() # Initialize Playwright page
            if not self.page:
                 logger.error("Playwright page not initialized in WebPageScreenshotTaker.")
                 raise RuntimeError("Playwright page not available for WebPageScreenshotTaker.")

            await self.page.goto(url, wait_until="networkidle", timeout=60000) # Wait for network idle
            
            # Use instance configured format and full_page setting
            await self.page.screenshot(path=file_path, full_page=self.full_page, type=self.image_format) # type: ignore (Playwright type for image_format is Literal["png", "jpeg"])
            
            absolute_file_path = os.path.abspath(file_path)
            logger.info(f"Screenshot saved successfully to {absolute_file_path}")
            return absolute_file_path
        except Exception as e:
            logger.error(f"Error taking screenshot of URL '{url}': {e}", exc_info=True)
            raise RuntimeError(f"WebPageScreenshotTaker failed for URL '{url}': {str(e)}")
        finally:
            await self.close() # Close Playwright page/context

