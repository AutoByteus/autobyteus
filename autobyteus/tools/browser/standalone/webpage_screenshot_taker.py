from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType 
from brui_core.ui_integrator import UIIntegrator 
import logging 
import os 

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext 

logger = logging.getLogger(__name__) 

class WebPageScreenshotTaker(BaseTool, UIIntegrator):
    """
    A class that takes a screenshot of a given webpage using Playwright and saves it.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self, config=config)
        UIIntegrator.__init__(self) 
        
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
            name="file_path", 
            param_type=ParameterType.STRING,
            description="The local file path (including filename and extension, e.g., 'screenshots/page.png') where the screenshot will be saved.",
            required=True
        ))
        return schema
        
    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: 
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

    async def _execute(self, context: 'AgentContext', url: str, file_path: str) -> str: 
        logger.info(f"WebPageScreenshotTaker for agent {context.agent_id} taking screenshot of '{url}', saving to '{file_path}'.")
        
        output_dir = os.path.dirname(file_path)
        if output_dir: 
            os.makedirs(output_dir, exist_ok=True)

        try:
            await self.initialize() 
            if not self.page:
                 logger.error("Playwright page not initialized in WebPageScreenshotTaker.")
                 raise RuntimeError("Playwright page not available for WebPageScreenshotTaker.")

            await self.page.goto(url, wait_until="networkidle", timeout=60000) 
            
            await self.page.screenshot(path=file_path, full_page=self.full_page, type=self.image_format) # type: ignore 
            
            absolute_file_path = os.path.abspath(file_path)
            logger.info(f"Screenshot saved successfully to {absolute_file_path}")
            return absolute_file_path
        except Exception as e:
            logger.error(f"Error taking screenshot of URL '{url}': {e}", exc_info=True)
            raise RuntimeError(f"WebPageScreenshotTaker failed for URL '{url}': {str(e)}")
        finally:
            await self.close()
