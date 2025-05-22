from typing import Optional, TYPE_CHECKING
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from brui_core.ui_integrator import UIIntegrator

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema

class WebPageScreenshotTaker(BaseTool, UIIntegrator):
    """
    A class that takes a screenshot of a given webpage using Playwright.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        
        # Extract configuration with defaults
        self.full_page = True  # Default
        self.image_format = "png"  # Default
        
        if config:
            self.full_page = config.get('full_page', True)
            self.image_format = config.get('image_format', 'png').lower()

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
        return '''WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file path. Usage:
    <command name="WebPageScreenshotTaker">
    <arg name="url">webpage_url</arg>
    <arg name="file_path">screenshot_file_path</arg>
    </command>
    where "webpage_url" is a string containing the URL of the webpage to take a screenshot of, and "screenshot_file_path" is the path where the screenshot will be saved.
    '''

    async def _execute(self, **kwargs):
        """
        Take a screenshot of the webpage at the given URL using Playwright and save it to the specified file path.

        Args:
            **kwargs: Keyword arguments containing the URL and file path. The URL should be specified as 'url', and the file path as 'file_path'.

        Returns:
            str: The file path of the saved screenshot.

        Raises:
            ValueError: If the 'url' or 'file_path' keyword arguments are not specified.
        """
        url = kwargs.get('url')
        file_path = kwargs.get('file_path')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")
        if not file_path:
            raise ValueError("The 'file_path' keyword argument must be specified.")

        await self.initialize()
        await self.page.goto(url)
        await self.page.screenshot(path=file_path, full_page=self.full_page, type=self.image_format)
        await self.close()
        return file_path
