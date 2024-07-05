from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator
from autobyteus.utils.html_cleaner import clean


class WebPageSourceExtractor(BaseTool, UIIntegrator):
    """
    A class that retrieves and cleans the HTML source from a given webpage using Playwright.
    """
    def __init__(self):
        super().__init__()

    def usage(self):
        """
        Return a string describing the usage of the WebPageSourceExtractor tool.
        """
        return "WebPageSourceExtractor(url), where 'url' is a string containing the webpage URL to retrieve the HTML source from."

    async def execute(self, **kwargs):
        """
        Retrieve and clean the HTML source from the webpage at the given URL using Playwright.

        Args:
            **kwargs: Keyword arguments containing the URL. The URL should be specified as 'url'.

        Returns:
            str: The cleaned HTML source of the webpage.

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
