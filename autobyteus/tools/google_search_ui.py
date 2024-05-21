import re
from bs4 import BeautifulSoup
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator

from autobyteus.utils.html import clean_html


class GoogleSearch(BaseTool, UIIntegrator):
    """
    A tool that allows for performing a Google search using Playwright and retrieving the search results.
    """
    def __init__(self):
        self.text_area_selector = 'textarea[title="Suche"]'

    async def execute(self, **kwargs):
        """
        Perform a Google search using Playwright and return the search results.

        Args:
            **kwargs: Keyword arguments containing the search query. The query should be specified as 'query'.

        Returns:
            list: A list of dictionaries containing the title, link, and snippet for each search result.
        """
        query = kwargs.get('query')
        if not query:
            raise ValueError("The 'query' keyword argument must be specified.")

        # Call the initialize method from the UIIntegrator class to set up the Playwright browser
        self.initialize()
        await self.page.goto('https://www.google.com/', waitUtil="networkidle")


        # Find the search box element, type in the search query, and press the Enter key
        textarea = self.page.locator(self.text_area_selector)
        await textarea.click()
        await self.page.type(self.textarea_selector, query)
        await self.page.keyboard.press('Enter')
        await self.page.wait_for_load_state('networkidle')

        # Wait for the search results to load
        self.page.wait_for_selector('#search', state='attached', timeout=10000)

        # Wait for the search results to load
        search_result_div = await self.page.wait_for_selector('#search', state='attached', timeout=10000)

        # Get the content of the div
        search_result = await search_result_div.inner_text()
        cleaned_search_result = clean_html(search_result)

        return cleaned_search_result

