"""
File: autobyteus/tools/browser/standalone/webpage_reader.py

This module provides a WebPageReader tool for reading and cleaning HTML content from webpages.

The WebPageReader class allows users to retrieve and clean the HTML content of a specified webpage
using Playwright. It inherits from BaseTool and UIIntegrator, providing a seamless integration
with web browsers.
"""

import logging
from typing import Optional, TYPE_CHECKING
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from brui_core.ui_integrator import UIIntegrator
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema

logger = logging.getLogger(__name__)

class WebPageReader(BaseTool, UIIntegrator):
    """
    A class that reads and cleans the HTML content from a given webpage using Playwright.

    This tool allows users to specify the level of content cleanup to be applied to the
    retrieved HTML content.

    Attributes:
        cleaning_mode (CleaningMode): The level of cleanup to apply to the HTML content.
            Defaults to CleaningMode.THOROUGH.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        """
        Initialize the WebPageReader with a specified content cleanup level.

        Args:
            config (ToolConfig, optional): Configuration containing cleanup level and other parameters.
        """
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        
        # Extract configuration with defaults
        cleaning_mode = CleaningMode.THOROUGH  # Default
        if config:
            cleaning_mode_value = config.get('cleaning_mode')
            if cleaning_mode_value:
                if isinstance(cleaning_mode_value, str):
                    try:
                        cleaning_mode = CleaningMode(cleaning_mode_value.upper())
                    except ValueError:
                        cleaning_mode = CleaningMode.THOROUGH
                elif isinstance(cleaning_mode_value, CleaningMode):
                    cleaning_mode = cleaning_mode_value
        
        self.cleaning_mode = cleaning_mode
        logger.debug(f"WebPageReader initialized with cleaning_mode: {self.cleaning_mode}")

    @classmethod
    def get_config_schema(cls) -> 'ToolConfigSchema':
        """
        Return the configuration schema for this tool.
        
        Returns:
            ToolConfigSchema: Schema describing the tool's configuration parameters.
        """
        schema = ToolConfigSchema()
        
        schema.add_parameter(ToolConfigParameter(
            name="cleaning_mode",
            param_type=ParameterType.ENUM,
            description="Level of HTML content cleanup to apply to the webpage content. BASIC removes only dangerous elements, THOROUGH removes most formatting for clean text extraction.",
            required=False,
            default_value="THOROUGH",
            enum_values=["BASIC", "THOROUGH"]
        ))
        
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the WebPageReader tool.

        Returns:
            str: An XML description of how to use the WebPageReader tool.
        """
        return '''WebPageReader: Reads the HTML content from a given webpage. Usage:
<command name="WebPageReader">
  <arg name="url">webpage_url</arg>
</command>
where "webpage_url" is a string containing the URL of the webpage to read the content from.
'''

    async def _execute(self, **kwargs):
        """
        Read and clean the HTML content from the webpage at the given URL using Playwright.

        Args:
            **kwargs: Keyword arguments containing the URL. The URL should be specified as 'url'.

        Returns:
            str: The cleaned HTML content of the webpage.

        Raises:
            ValueError: If the 'url' keyword argument is not specified.
        """
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        await self.initialize()
        await self.page.goto(url, timeout=0)
        page_content = await self.page.content()
        cleaned_content = clean(page_content, mode=self.cleaning_mode)
        await self.close()
        return f'''here is the html of the web page
                <WebPageContentStart>
                    {cleaned_content}
                </WebPageContentEnd>
                '''
