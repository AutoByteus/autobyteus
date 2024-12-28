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

    def tool_usage(self):
        """
        Return a string describing the usage of the GoogleSearch tool.
        """
        return 'GoogleSearch: Searches the internet for information. Usage: <<<GoogleSearch(query="search query")>>>, where "search query" is a string.'

    def tool_usage_xml(self):
        """
        Return an XML string describing the usage of the GoogleSearch tool.
        """
        return '''GoogleSearch: Searches the internet for information. Usage:
    <command name="GoogleSearch">
    <arg name="query">search query</arg>
    </command>
    where "search query" is a string.
    '''

    async def _execute(self, **kwargs):
        """
        Perform a Google search using Playwright and return the search results.

        This method initializes the Playwright browser, navigates to Google, performs the search,
        and retrieves the results. After initialization, self.page is available as a Playwright
        page object for interacting with the web browser.

        Args:
            **kwargs: Keyword arguments containing the search query. The query should be specified as 'query'.

        Returns:
            str: A string containing the cleaned HTML of the search results.

        Raises:
            ValueError: If the 'query' keyword argument is not specified.
        """
        query = kwargs.get('query')
        if not query:
            raise ValueError("The 'query' keyword argument must be specified.")

        # Call the initialize method from the UIIntegrator class to set up the Playwright browser
        await self.initialize()
        # After initialization, self.page is now available as a Playwright page object

        await self.page.goto('https://www.google.com/')

        # Find the search box element, type in the search query, and press the Enter key
        textarea = self.page.locator(self.text_area_selector)
        await textarea.click()
        await self.page.type(self.text_area_selector, query)
        await self.page.keyboard.press('Enter')
        await self.page.wait_for_load_state()

        # Wait for the search results to load
        # Wait for the search results to load, we didnt use main because main will contain a lot of base64 encoded images. This will consume a lot of tokens.
        #search_result_div = await self.page.wait_for_selector('div.main', state="visible", timeout=10000)
        search_result_div = await self.page.wait_for_selector('#search', state="visible", timeout=10000)
        await asyncio.sleep(2)
        # Get the content of the div
        search_result = await search_result_div.inner_html()
        cleaned_search_result = clean(search_result, mode=self.cleaning_mode)
        await self.close()
        return f'''here is the google search result html
                  <GoogleSearchResultStart>
                        {cleaned_search_result}
                  </GoogleSearchResultEnd>
                '''