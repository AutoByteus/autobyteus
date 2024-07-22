# File: autobyteus/tools/google_search_ui.py
import re
from bs4 import BeautifulSoup
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator

from autobyteus.utils.html_cleaner import clean


class GoogleSearch(BaseTool, UIIntegrator):
    """
    A tool that allows for performing a Google search using Playwright and retrieving the search results.

    This class inherits from BaseTool and UIIntegrator. Upon initialization via the UIIntegrator's
    initialize method, self.page becomes available as a Playwright page object for interaction
    with the web browser.
    """

    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

        self.text_area_selector = 'textarea[title="Suche"]'

    def tool_usage(self):
        """
        Return a string describing the usage of the GoogleSearch tool.
        """
        return 'GoogleSearch: Searches the internet for information. Usage: <<<GoogleSearch(query="search query")>>>, where "search query" is a string.'

    def tool_usage_xml(self):
        return '''GoogleSearch: Searches the internet for information. Usage:
    <command name="GoogleSearch">
    <arg name="query">search query</arg>
    </command>
    where "search query" is a string.
    '''

    async def execute(self, **kwargs):
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
        search_result_div = await self.page.wait_for_selector('#search', state="visible", timeout=10000)

        # Get the content of the div
        search_result = await search_result_div.inner_html()
        cleaned_search_result = clean(search_result)
        await self.close()
        return cleaned_search_result