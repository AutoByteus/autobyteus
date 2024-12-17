from autobyteus.tools.base_tool import BaseTool
from brui_core.ui_integrator import UIIntegrator


class WebPageScreenshotTaker(BaseTool, UIIntegrator):
    """
    A class that takes a screenshot of a given webpage using Playwright.
    """
    def __init__(self):
        BaseTool.__init__(self)
        UIIntegrator.__init__(self)

    def tool_usage(self):
        return "WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file path. Usage: <<<WebPageScreenshotTaker(url='webpage_url', file_path='screenshot_file_path')>>>, where 'webpage_url' is a string containing the URL of the webpage to take a screenshot of, and 'screenshot_file_path' is the path where the screenshot will be saved."

    def tool_usage_xml(self):
            return '''WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file path. Usage:
    <command name="WebPageScreenshotTaker">
    <arg name="url">webpage_url</arg>
    <arg name="file_path">screenshot_file_path</arg>
    </command>
    where "webpage_url" is a string containing the URL of the webpage to take a screenshot of, and "screenshot_file_path" is the path where the screenshot will be saved.
    '''

    async def _execute(self, **kwargs):
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
        await self.page.goto(url)
        await self.page.screenshot(path=file_path, full_page=True)
        await self.close()
        return file_path