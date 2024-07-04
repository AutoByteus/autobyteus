# file: autobyteus/autobyteus/tools/web_page_reader.py
from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.utils.html_cleaner import clean


class WebPageReader(BaseTool, UIIntegrator):
    """
    A class that reads and cleans the content from a given webpage using Playwright.
    """
    def __init__(self):
        super().__init__()

    def usage(self):
        """
        Return a string describing the usage of the WebPageReader tool.
        """
        return "WebPageReader(url), where 'url' is a string containing the webpage URL to read and clean."

    async def execute(self, **kwargs):
        """
        Read and clean the content from the webpage at the given URL using Playwright.

        Args:
            **kwargs: Keyword arguments containing the URL. The URL should be specified as 'url'.

        Returns:
            str: The cleaned content of the webpage.
        """
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        # Call the initialize method from the UIIntegrator class to set up the Playwright browser
        await self.initialize()

        try:
            # Navigate to the URL and wait for the page to load
            await self.page.goto(url, wait_until="networkidle")

            # Extract the HTML content of the page
            page_content = await self.page.content()

            # Clean the HTML content
            cleaned_content = clean(page_content)

            return cleaned_content
        except Exception as e:
            print(f"Error occurred while reading content from {url}: {str(e)}")
            return ""