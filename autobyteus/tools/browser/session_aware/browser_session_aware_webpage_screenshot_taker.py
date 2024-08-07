# File: autobyteus/tools/browser/session_aware/browser_session_aware_webpage_screenshot_taker.py

from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession

class BrowserSessionAwareWebPageScreenshotTaker(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "WebPageScreenshotTaker"

    def tool_usage(self):
        return "WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file path. Usage: <<<WebPageScreenshotTaker(webpage_url='url_to_screenshot', file_path='screenshot_file_path')>>>, where 'url_to_screenshot' is a string containing the URL of the webpage to take a screenshot of, and 'screenshot_file_path' is the path where the screenshot will be saved."

    def tool_usage_xml(self):
        return '''WebPageScreenshotTaker: Takes a screenshot of a given webpage and saves it to the specified file path. Usage:
<command name="WebPageScreenshotTaker">
  <arg name="webpage_url">url_to_screenshot</arg>
  <arg name="file_path">screenshot_file_path</arg>
</command>
where "url_to_screenshot" is a string containing the URL of the webpage to take a screenshot of, and "screenshot_file_path" is the path where the screenshot will be saved.
'''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        file_path = kwargs.get('file_path')
        if not file_path:
            raise ValueError("The 'file_path' keyword argument must be specified.")

        await shared_session.page.screenshot(path=file_path, full_page=True)
        return file_path