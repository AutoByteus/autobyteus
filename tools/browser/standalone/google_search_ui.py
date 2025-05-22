"""
File: autobyteus/tools/browser/google_search_ui.py

This module provides a GoogleSearch tool for performing Google searches using Playwright.

The GoogleSearch class allows users to search Google and retrieve cleaned search results.
It inherits from BaseTool and UIIntegrator, providing a seamless integration with web browsers.

Classes:
    GoogleSearch: A tool for performing Google searches and retrieving cleaned results.
"""

import asyncio
import re
import logging
from typing import Optional, TYPE_CHECKING, Any
from bs4 import BeautifulSoup
from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.tool_config import ToolConfig
from autobyteus.tools.tool_config_schema import ToolConfigSchema, ToolConfigParameter, ParameterType
from brui_core.ui_integrator import UIIntegrator

from autobyteus.utils.html_cleaner import clean, CleaningMode

if TYPE_CHECKING:
    from autobyteus.tools.tool_config_schema import ToolConfigSchema
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

class GoogleSearch(BaseTool, UIIntegrator):
    """
    A tool that allows for performing a Google search using Playwright and retrieving the search results.

    This class inherits from BaseTool and UIIntegrator. Upon initialization via the UIIntegrator's
    initialize method, self.page becomes available as a Playwright page object for interaction
    with the web browser.

    Attributes:
        text_area_selector (str): The CSS selector for the Google search text area.
        cleaning_mode (CleaningMode): The level of cleanup to apply to the HTML content.
    """

    def __init__(self, config: Optional[ToolConfig] = None):
        """
        Initialize the GoogleSearch tool with a specified content cleanup level.

        Args:
            config (ToolConfig, optional): Configuration containing cleanup level and other parameters.
        """
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

        self.text_area_selector = 'textarea[name="q"]'
        
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
        logger.debug(f"GoogleSearch initialized with cleaning_mode: {self.cleaning_mode}")

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
            description="Level of HTML content cleanup to apply to search results. BASIC removes only dangerous elements, THOROUGH removes most formatting for clean text extraction.",
            required=False,
            default_value="THOROUGH",
            enum_values=["BASIC", "THOROUGH"]
        ))
        
        return schema

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the GoogleSearch tool.

        Returns:
            str: An XML description of how to use the GoogleSearch tool.
        """
        return '''GoogleSearch: Searches the internet for information. Usage:
    <command name="GoogleSearch">
    <arg name="query">search query</arg>
    </command>
    where "search query" is a string.
    '''

    async def _execute(self, context: 'AgentContext', **kwargs) -> Any:
        query = kwargs.get('query')
        if not query:
            raise ValueError("The 'query' keyword argument must be specified.")

        logger.info(f"Agent '{context.agent_id}' performing Google search for query: '{query}'")
        await self.initialize() # From UIIntegrator
        try:
            await self.page.goto('https://www.google.com/')

            textarea = self.page.locator(self.text_area_selector)
            await textarea.click()
            await self.page.type(self.text_area_selector, query)
            # Using wait_for_load_state("networkidle") or similar after pressing Enter
            # can be more robust than a fixed sleep.
            await asyncio.gather(
                self.page.wait_for_load_state("networkidle"),
                self.page.keyboard.press('Enter')
            )
            
            # Wait for search results container to be visible
            search_result_div = await self.page.wait_for_selector('#search', state="visible", timeout=10000)
            # await asyncio.sleep(2) # Consider removing fixed sleep if wait_for_load_state is effective
            search_result_html = await search_result_div.inner_html()
            
            cleaned_search_result = clean(search_result_html, mode=self.cleaning_mode)
            
            logger.info(f"Agent '{context.agent_id}' Google search completed for query: '{query}'. Result length: {len(cleaned_search_result)}")
            return f'''here is the google search result html
                    <GoogleSearchResultStart>
                            {cleaned_search_result}
                    </GoogleSearchResultEnd>
                    '''
        finally:
            await self.close() # From UIIntegrator
