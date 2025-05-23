# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_screenshot_taker.py

import os
import logging # Added
from typing import Optional, TYPE_CHECKING, Any
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_config import ToolConfig # For instantiation config
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Updated

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext # Not used by perform_action directly

logger = logging.getLogger(__name__) # Added

class BrowserSessionAwareWebPageScreenshotTaker(BrowserSessionAwareTool):
    """
    A session-aware tool to take a screenshot of the current page in a shared browser session.
    Screenshot settings (full_page, image_format) can be configured at instantiation.
    """
    def __init__(self, config: Optional[ToolConfig] = None): # Instantiation config
        super().__init__()
        
        self.full_page: bool = True 
        self.image_format: str = "png" 
        
        if config:
            self.full_page = config.get('full_page', True)
            self.image_format = str(config.get('image_format', 'png')).lower()
            if self.image_format not in ["png", "jpeg"]:
                logger.warning(f"Invalid image_format '{self.image_format}' in config. Defaulting to 'png'.")
                self.image_format = "png"
        logger.debug(f"BrowserSessionAwareWebPageScreenshotTaker initialized. Full page: {self.full_page}, Format: {self.image_format}")

    @classmethod
    def get_name(cls) -> str: # Ensure registered name is as expected
        return "WebPageScreenshotTaker" # Was "WebPageScreenshotTaker" in its tool_usage_xml

    @classmethod
    def get_description(cls) -> str:
        return ("Takes a screenshot of the current page in a shared browser session. "
                "Saves it to the specified local file path and returns the absolute path of the saved screenshot. "
                "Screenshot options (full page, image format) can be set at tool instantiation.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        # webpage_url is required by BrowserSessionAwareTool base class
        schema.add_parameter(ParameterDefinition(
            name="webpage_url", 
            param_type=ParameterType.STRING,
            description="URL of the webpage. Required if no browser session is active or to ensure context. Screenshot is of current page.",
            required=True 
        ))
        schema.add_parameter(ParameterDefinition(
            name="file_name", # Argument for the output file name/path
            param_type=ParameterType.FILE_PATH,
            description="The local file path (including filename and extension, e.g., 'session_screenshots/page.png') where the screenshot will be saved.",
            required=True
        ))
        return schema

    @classmethod
    def get_config_schema(cls) -> Optional[ParameterSchema]: # For instantiation
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="full_page",
            param_type=ParameterType.BOOLEAN,
            description="Default for whether to capture the full scrollable page or just the viewport.",
            required=False,
            default_value=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="image_format",
            param_type=ParameterType.ENUM,
            description="Default image format for screenshots (png or jpeg).",
            required=False,
            default_value="png",
            enum_values=["png", "jpeg"]
        ))
        return schema

    async def perform_action(
        self, 
        shared_session: SharedBrowserSession, 
        file_name: str, # Argument from schema
        webpage_url: str # Consumed by base class _execute, available here if needed
    ) -> str: # Updated signature
        """
        Takes a screenshot of the current page in the shared session.
        'file_name' and 'webpage_url' are validated by BaseTool.execute().
        """
        logger.info(f"BrowserSessionAwareWebPageScreenshotTaker performing action. Saving to '{file_name}'. Current page: {shared_session.page.url}")

        # Ensure parent directory for file_name exists
        output_dir = os.path.dirname(file_name)
        if output_dir: # If file_name includes a directory
            os.makedirs(output_dir, exist_ok=True)
            
        try:
            # Use instance configured format and full_page setting
            await shared_session.page.screenshot(
                path=file_name, 
                full_page=self.full_page, 
                type=self.image_format # type: ignore
            )
            absolute_file_path = os.path.abspath(file_name)
            logger.info(f"Screenshot of {shared_session.page.url} saved successfully to {absolute_file_path}")
            return absolute_file_path
        except Exception as e:
            logger.error(f"Error taking screenshot in shared session for page {shared_session.page.url}, saving to '{file_name}': {e}", exc_info=True)
            raise RuntimeError(f"Failed to take screenshot in shared session: {str(e)}")

