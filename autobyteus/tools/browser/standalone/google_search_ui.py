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
from bs4 import BeautifulSoup
from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator

from autobyteus.utils.html_cleaner import clean, CleaningMode


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

    def __init__(self, cleaning_mode=CleaningMode.THOROUGH):
        """
        Initialize the GoogleSearch tool with a specified content cleanup level.

        Args:
            cleaning_mode (CleaningMode, optional): The level of cleanup to apply to
                the HTML content. Defaults to CleaningMode.THOROUGH.
        """
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

        self.text_area_selector = 'textarea[name="q"]'
        self.cleaning_mode = cleaning_mode

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

    async def _execute(self, **kwargs):
        query = kwargs.get('query')
        if not query:
            raise ValueError("The 'query' keyword argument must be specified.")

        await self.initialize()
        await self.page.goto('https://www.google.com/')

        textarea = self.page.locator(self.text_area_selector)
        await textarea.click()
        await self.page.type(self.text_area_selector, query)
        await self.page.keyboard.press('Enter')
        await self.page.wait_for_load_state()

        search_result_div = await self.page.wait_for_selector('#search', state="visible", timeout=10000)
        await asyncio.sleep(2)
        search_result = await search_result_div.inner_html()
        cleaned_search_result = clean(search_result, mode=self.cleaning_mode)
        await self.close()
        return f'''here is the google search result html
                  <GoogleSearchResultStart>
                        {cleaned_search_result}
                  </GoogleSearchResultEnd>
                '''
