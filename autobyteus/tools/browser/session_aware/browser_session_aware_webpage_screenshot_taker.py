# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_screenshot_taker.py

import os
from typing import Optional, TYPE_CHECKING
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema

class BrowserSessionAwareWebPageScreenshotTaker(BrowserSessionAwareTool):
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__()
        
        # Extract configuration with defaults
        self.full_page = True  # Default
        self.image_format = "png"  # Default
        
        if config:
            self.full_page = config.get('full_page', True)
            self.image_format = config.get('image_format', 'png').lower()

    def get_name(self) -> str:
        return "WebPageScreenshotTaker"

    @classmethod
    def get_config_schema(cls) -> 'ToolConfigSchema':
        """
        Return the configuration schema for this tool.
        
        Returns:
            ToolConfigSchema: Schema describing the tool's configuration parameters.
        """
        schema = ToolConfigSchema()
        
        schema.add_parameter(ToolConfigParameter(
            name="full_page",
            param_type=ParameterType.BOOLEAN,
            description="Whether to capture the full scrollable page content or just the visible viewport.",
            required=False,
            default_value=True
        ))
        
        schema.add_parameter(ToolConfigParameter(
            name="image_format",
            param_type=ParameterType.ENUM,
            description="Image format for the screenshot file.",
            required=False,
            default_value="png",
            enum_values=["png", "jpeg"]
        ))
        
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the WebPageScreenshotTaker tool.

        Returns:
            str: An XML description of how to use the WebPageScreenshotTaker tool.
        """
        return '''WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file. Usage:
<command name="WebPageScreenshotTaker">
  <arg name="webpage_url">url_to_screenshot</arg>
  <arg name="file_name">screenshot_file_name</arg>
</command>
where "url_to_screenshot" is a string containing the URL of the webpage to take a screenshot of, and "screenshot_file_name" is the name of the file to save the screenshot (including extension, e.g., 'screenshot.png'). Optionally, "screenshot_file_name" can include a relative path (e.g., 'images/screenshot.png').
Returns the absolute file path of the saved screenshot.
'''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        file_name = kwargs.get('file_name')
        if not file_name:
            raise ValueError("The 'file_name' keyword argument must be specified.")

        await shared_session.page.screenshot(path=file_name, full_page=self.full_page, type=self.image_format)
        absolute_path = os.path.abspath(file_name)
        return absolute_path
