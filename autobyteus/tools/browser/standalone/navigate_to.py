from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator
from urllib.parse import urlparse

class NavigateTo(BaseTool, UIIntegrator):
    """
    A standalone tool for navigating to a specified website using Playwright.
    """

    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

    @classmethod
    def tool_usage_xml(cls):
        """
        Return an XML string describing the usage of the NavigateTo tool.

        Returns:
            str: An XML description of how to use the NavigateTo tool.
        """
        return '''
        NavigateTo: Navigates to a specified website. Usage:
        <command name="NavigateTo">
            <arg name="url">https://example.com</arg>
        </command>
        where "https://example.com" is the URL of the website to navigate to.
        '''

    async def _execute(self, **kwargs):
        url = kwargs.get('url')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")

        if not self._is_valid_url(url):
            raise ValueError(f"Invalid URL: {url}")

        try:
            await self.initialize()
            response = await self.page.goto(url, wait_until="domcontentloaded")
            if response.ok:
                return f"Successfully navigated to {url}"
            else:
                return f"Navigation to {url} failed with status {response.status}"
        finally:
            await self.close()

    @staticmethod
    def _is_valid_url(url):
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False
