from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool

class BrowserSessionAwareWebPageScreenshotTaker(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

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

    async def execute(self, **kwargs):
        url = kwargs.get('url')
        file_path = kwargs.get('file_path')
        if not url:
            raise ValueError("The 'url' keyword argument must be specified.")
        if not file_path:
            raise ValueError("The 'file_path' keyword argument must be specified.")

        shared_session = await self.get_or_create_shared_browser_session()

        await shared_session.page.goto(url)
        await shared_session.page.screenshot(path=file_path, full_page=True)
        return file_path