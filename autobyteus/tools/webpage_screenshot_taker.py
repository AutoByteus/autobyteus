from autobyteus.tools.base_tool import BaseTool
from llm_ui_integration.ui_integrator import UIIntegrator


class WebPageScreenshotTaker(BaseTool, UIIntegrator):
    """
    A class that takes a screenshot of a given webpage using Playwright.
    """
    def __init__(self):
        super().__init__()

    def usage(self):
        """
        Return a string describing the usage of the WebPageScreenshotTaker tool.
        """
        return "WebPageScreenshotTaker(url, file_path), where 'url' is a string containing the webpage URL to take a screenshot of, and 'file_path' is the path where the screenshot will be saved."

    async def execute(self, **kwargs):
        """
        Take a screenshot of the webpage at the given URL using Playwright and save it to the specified file path.

        Args:
            **kwargs: Keyword arguments containing the URL and file path. The URL should be specified as 'url', and the file path as 'file_path'.

        Returns:
            str: The file path of the saved screenshot.

        Raises:
            ValueError: If the 'url' or 'file_path' keyword arguments are not specified.
        """
        url = kwargs.get('url')
        file_path = kwargs.get('file_path')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")
        if not file_path:
            raise ValueError("The 'file_path' keyword argument must be specified.")

        await self.initialize()
        await self.page.goto(url, wait_until="networkidle")
    
        
        await self.page.screenshot(path=file_path, full_page=True)
        await self.close()
        return file_path