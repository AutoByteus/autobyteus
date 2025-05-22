# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_reader.py

import logging
from typing import Optional, TYPE_CHECKING
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema

logger = logging.getLogger(__name__)

class BrowserSessionAwareWebPageReader(BrowserSessionAwareTool):
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__()
        
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
        logger.debug(f"BrowserSessionAwareWebPageReader initialized with cleaning_mode: {self.cleaning_mode}")

    def get_name(self) -> str:
        return "WebPageReader"

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
        return '''WebPageReader: Reads and cleans the HTML content from a given webpage. Usage:
<command name="WebPageReader">
  <arg name="webpage_url">url_to_read</arg>
</command>
where "url_to_read" is a string containing the URL of the webpage to read the content from.
'''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        page_content = await shared_session.page.content()
        cleaned_content = clean(page_content, self.cleaning_mode)
        return cleaned_content
