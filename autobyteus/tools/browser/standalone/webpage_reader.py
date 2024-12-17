"""
File: autobyteus/tools/browser/standalone/webpage_reader.py

This module provides a WebPageReader tool for reading and cleaning HTML content from webpages.

The WebPageReader class allows users to retrieve and clean the HTML content of a specified webpage
using Playwright. It inherits from BaseTool and UIIntegrator, providing a seamless integration
with web browsers.

Classes:
    WebPageReader: A tool for reading and cleaning HTML content from webpages.
"""

from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator
from autobyteus.utils.html_cleaner import clean, CleaningMode

class WebPageReader(BaseTool, UIIntegrator):
    """
    A class that reads and cleans the HTML content from a given webpage using Playwright.

    This tool allows users to specify the level of content cleanup to be applied to the
    retrieved HTML content.

    Attributes:
        cleaning_mode (CleaningMode): The level of cleanup to apply to the HTML content.
            Defaults to CleaningMode.THOROUGH.
    """

    def __init__(self, cleaning_mode=CleaningMode.THOROUGH):
        """
        Initialize the WebPageReader with a specified content cleanup level.

        Args:
            cleaning_mode (CleaningMode, optional): The level of cleanup to apply to
                the HTML content. Defaults to CleaningMode.THOROUGH.
        """
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)
        self.cleaning_mode = cleaning_mode

    def tool_usage(self):
        return 'WebPageReader: Reads and cleans the HTML content from a given webpage. Usage: <<<WebPageReader(url="webpage_url")>>>, where "webpage_url" is a string containing the URL of the webpage to read the content from.'

    def tool_usage_xml(self):
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
