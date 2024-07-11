from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.utils.html_cleaner import clean


class WebPageReader(BaseTool, UIIntegrator):
    """
    A class that reads and cleans the HTML content from a given webpage using Playwright.
    """
    def __init__(self):
        super().__init__()

    def tool_usage(self):
        return 'WebPageReader: Reads and cleans the HTML content from a given webpage. Usage: <<<WebPageReader(url="webpage_url")>>>, where "webpage_url" is a string containing the URL of the webpage to read the content from.'

    def tool_usage_xml(self):
        return '''
WebPageReader: Reads and cleans the HTML content from a given webpage. Usage:
<command name="WebPageReader">
  <arg name="url">webpage_url</arg>
</command>
where "webpage_url" is a string containing the URL of the webpage to read the content from.
'''
    async def execute(self, **kwargs):
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
        await self.page.goto(url, wait_until="networkidle")
        page_content = await self.page.content()
        cleaned_content = clean(page_content)
        return cleaned_content